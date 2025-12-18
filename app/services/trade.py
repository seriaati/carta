from collections.abc import Sequence
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.db import get_db
from app.core.enums import EventType, TradeStatus
from app.models.event_log import EventLog
from app.models.inventory import Inventory
from app.models.trade import Trade
from app.schemas.common import PaginationData
from app.schemas.trade import TradeCreate, TradeUpdate
from app.services.deck_card import DeckCardService
from app.services.inventory import InventoryService
from app.services.player import PlayerService


class TradeService:
    def __init__(
        self,
        db: Annotated[AsyncSession, Depends(get_db)],
        player_service: Annotated[PlayerService, Depends()],
        inventory_service: Annotated[InventoryService, Depends()],
        deck_card_service: Annotated[DeckCardService, Depends()],
    ) -> None:
        self.db = db
        self.player_service = player_service
        self.inventory_service = inventory_service
        self.deck_card_service = deck_card_service

    async def get_trades(
        self, *, page: int, page_size: int
    ) -> tuple[Sequence[Trade], PaginationData]:
        offset = (page - 1) * page_size

        total_items_result = await self.db.exec(select(Trade))
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(select(Trade).offset(offset).limit(page_size))
        trades = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return trades, pagination

    async def get_trade(self, trade_id: int) -> Trade | None:
        result = await self.db.exec(select(Trade).where(Trade.id == trade_id))
        return result.first()

    async def get_player_trades(
        self, player_id: int, *, page: int, page_size: int, status: TradeStatus | None = None
    ) -> tuple[Sequence[Trade], PaginationData]:
        """Get all trades where player is proposer or receiver."""
        offset = (page - 1) * page_size

        query = select(Trade).where(
            (Trade.proposer_id == player_id) | (Trade.receiver_id == player_id)
        )

        if status:
            query = query.where(Trade.status == status)

        total_items_result = await self.db.exec(query)
        total_items = len(total_items_result.all())

        total_pages = (total_items + page_size - 1) // page_size

        result = await self.db.exec(query.offset(offset).limit(page_size))
        trades = result.all()

        pagination = PaginationData(
            page=page, page_size=page_size, total_items=total_items, total_pages=total_pages
        )

        return trades, pagination

    async def create_trade_request(self, proposer_id: int, trade_data: TradeCreate) -> Trade:
        """Create a new trade request from proposer to receiver."""
        # Validate proposer exists
        proposer = await self.player_service.get_player(proposer_id)
        if not proposer:
            msg = "找不到提議者"
            raise HTTPException(status_code=404, detail=msg)

        # Validate receiver exists
        receiver = await self.player_service.get_player(trade_data.receiver_id)
        if not receiver:
            msg = "找不到接收者"
            raise HTTPException(status_code=404, detail=msg)

        # Cannot trade with self
        if proposer_id == trade_data.receiver_id:
            msg = "不能與自己交易"
            raise HTTPException(status_code=400, detail=msg)

        # Validate proposer owns the offered card
        offered_cards = await self.inventory_service.get_player_cards(
            proposer_id, card_id=trade_data.offered_card_id
        )
        if not offered_cards or offered_cards[0][1] < 1:
            msg = "你沒有這張卡片"
            raise HTTPException(status_code=400, detail=msg)

        # If requesting a card, validate receiver owns it
        if trade_data.requested_card_id:
            requested_cards = await self.inventory_service.get_player_cards(
                trade_data.receiver_id, card_id=trade_data.requested_card_id
            )
            if not requested_cards or requested_cards[0][1] < 1:
                msg = "對方沒有這張卡片"
                raise HTTPException(status_code=400, detail=msg)

        # If requesting money, validate receiver has enough
        if trade_data.price and receiver.currency < trade_data.price:
            msg = f"對方貨幣不足。擁有: {receiver.currency}, 需要: {trade_data.price}"
            raise HTTPException(status_code=400, detail=msg)

        # Create the trade
        trade = Trade(
            proposer_id=proposer_id,
            receiver_id=trade_data.receiver_id,
            offered_card_id=trade_data.offered_card_id,
            requested_card_id=trade_data.requested_card_id,
            price=trade_data.price,
            status=TradeStatus.PENDING,
        )

        self.db.add(trade)
        await self.db.flush()  # To get trade.id

        # Log event for proposer
        await self._log_trade_event(
            proposer_id,
            EventType.TRADE_CREATED,
            {
                "trade_id": trade.id,
                "receiver_id": trade_data.receiver_id,
                "offered_card_id": trade_data.offered_card_id,
                "requested_card_id": trade_data.requested_card_id,
                "price": trade_data.price,
            },
        )

        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def accept_trade(self, trade_id: int, receiver_id: int) -> Trade:
        """Accept a pending trade and execute the exchange."""
        trade = await self.get_trade(trade_id)
        if not trade:
            msg = "找不到交易"
            raise HTTPException(status_code=404, detail=msg)

        # Validate receiver
        if trade.receiver_id != receiver_id:
            msg = "你不是這個交易的接收者"
            raise HTTPException(status_code=403, detail=msg)

        # Validate trade is pending
        if trade.status != TradeStatus.PENDING:
            msg = f"交易狀態錯誤。目前狀態: {trade.status}"
            raise HTTPException(status_code=400, detail=msg)

        # Re-validate proposer still owns the offered card
        offered_cards = await self.inventory_service.get_player_cards(
            trade.proposer_id, card_id=trade.offered_card_id
        )
        if not offered_cards or offered_cards[0][1] < 1:
            trade.status = TradeStatus.CANCELLED
            self.db.add(trade)
            await self.db.commit()
            msg = "提議者不再擁有該卡片, 交易已取消"
            raise HTTPException(status_code=400, detail=msg)

        # If card-for-card trade, validate receiver still owns the requested card
        if trade.requested_card_id:
            requested_cards = await self.inventory_service.get_player_cards(
                trade.receiver_id, card_id=trade.requested_card_id
            )
            if not requested_cards or requested_cards[0][1] < 1:
                trade.status = TradeStatus.CANCELLED
                self.db.add(trade)
                await self.db.commit()
                msg = "你不再擁有該卡片, 交易已取消"
                raise HTTPException(status_code=400, detail=msg)

        # If card-for-money trade, validate receiver still has enough money
        if trade.price:
            receiver = await self.player_service.get_player(trade.receiver_id)
            if not receiver or receiver.currency < trade.price:
                trade.status = TradeStatus.CANCELLED
                self.db.add(trade)
                await self.db.commit()
                msg = (
                    f"貨幣不足, 交易已取消。擁有: {receiver.currency if receiver else 0}, "
                    f"需要: {trade.price}"
                )
                raise HTTPException(status_code=400, detail=msg)

        # Execute the trade
        await self._execute_trade_exchange(trade)

        # Update trade status
        trade.status = TradeStatus.COMPLETED
        self.db.add(trade)

        # Log acceptance
        await self._log_trade_event(
            receiver_id,
            EventType.TRADE_ACCEPTED,
            {"trade_id": trade_id, "proposer_id": trade.proposer_id},
        )

        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def reject_trade(self, trade_id: int, receiver_id: int) -> Trade:
        """Reject a pending trade."""
        trade = await self.get_trade(trade_id)
        if not trade:
            msg = "找不到交易"
            raise HTTPException(status_code=404, detail=msg)

        # Validate receiver
        if trade.receiver_id != receiver_id:
            msg = "你不是這個交易的接收者"
            raise HTTPException(status_code=403, detail=msg)

        # Validate trade is pending
        if trade.status != TradeStatus.PENDING:
            msg = f"交易狀態錯誤。目前狀態: {trade.status}"
            raise HTTPException(status_code=400, detail=msg)

        trade.status = TradeStatus.REJECTED
        self.db.add(trade)

        await self._log_trade_event(
            receiver_id,
            EventType.TRADE_REJECTED,
            {"trade_id": trade_id, "proposer_id": trade.proposer_id},
        )

        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def cancel_trade(self, trade_id: int, proposer_id: int) -> Trade:
        """Cancel a pending trade (proposer only)."""
        trade = await self.get_trade(trade_id)
        if not trade:
            msg = "找不到交易"
            raise HTTPException(status_code=404, detail=msg)

        # Validate proposer
        if trade.proposer_id != proposer_id:
            msg = "你不是這個交易的提議者"
            raise HTTPException(status_code=403, detail=msg)

        # Validate trade is pending
        if trade.status != TradeStatus.PENDING:
            msg = f"交易狀態錯誤。目前狀態: {trade.status}"
            raise HTTPException(status_code=400, detail=msg)

        trade.status = TradeStatus.CANCELLED
        self.db.add(trade)

        await self._log_trade_event(
            proposer_id,
            EventType.TRADE_CANCELLED,
            {"trade_id": trade_id, "receiver_id": trade.receiver_id},
        )

        await self.db.commit()
        await self.db.refresh(trade)
        return trade

    async def update_trade(self, trade_id: int, trade: TradeUpdate) -> Trade | None:
        """Update trade (admin only)."""
        existing_trade = await self.get_trade(trade_id)
        if not existing_trade:
            return None

        trade_data = trade.model_dump(exclude_unset=True)
        existing_trade.sqlmodel_update(trade_data)
        self.db.add(existing_trade)
        await self.db.commit()
        await self.db.refresh(existing_trade)
        return existing_trade

    async def delete_trade(self, trade_id: int) -> bool:
        """Delete trade (admin only)."""
        trade = await self.get_trade(trade_id)
        if not trade:
            return False

        await self.db.delete(trade)
        await self.db.commit()
        return True

    # Private helper methods

    async def _log_trade_event(self, player_id: int, event_type: EventType, context: dict) -> None:
        """Log a trade event to the event log."""
        event_log = EventLog(player_id=player_id, event_type=event_type, context=context)
        self.db.add(event_log)

    async def _execute_trade_exchange(self, trade: Trade) -> None:
        """Execute the actual card/money exchange for a trade."""
        # Transfer offered card from proposer to receiver
        await self._transfer_card(trade.proposer_id, trade.receiver_id, trade.offered_card_id)
        await self._log_trade_event(
            trade.proposer_id,
            EventType.TRADE_CARD_SENT,
            {
                "trade_id": trade.id,
                "card_id": trade.offered_card_id,
                "to_player_id": trade.receiver_id,
            },
        )
        await self._log_trade_event(
            trade.receiver_id,
            EventType.TRADE_CARD_RECEIVED,
            {
                "trade_id": trade.id,
                "card_id": trade.offered_card_id,
                "from_player_id": trade.proposer_id,
            },
        )

        # If card-for-card trade
        if trade.requested_card_id:
            await self._transfer_card(trade.receiver_id, trade.proposer_id, trade.requested_card_id)
            await self._log_trade_event(
                trade.receiver_id,
                EventType.TRADE_CARD_SENT,
                {
                    "trade_id": trade.id,
                    "card_id": trade.requested_card_id,
                    "to_player_id": trade.proposer_id,
                },
            )
            await self._log_trade_event(
                trade.proposer_id,
                EventType.TRADE_CARD_RECEIVED,
                {
                    "trade_id": trade.id,
                    "card_id": trade.requested_card_id,
                    "from_player_id": trade.receiver_id,
                },
            )

        # If card-for-money trade
        if trade.price:
            await self._transfer_currency(trade.receiver_id, trade.proposer_id, trade.price)
            await self._log_trade_event(
                trade.receiver_id,
                EventType.TRADE_MONEY_SENT,
                {"trade_id": trade.id, "amount": trade.price, "to_player_id": trade.proposer_id},
            )
            await self._log_trade_event(
                trade.proposer_id,
                EventType.TRADE_MONEY_RECEIVED,
                {"trade_id": trade.id, "amount": trade.price, "from_player_id": trade.receiver_id},
            )

    async def _transfer_card(self, from_player_id: int, to_player_id: int, card_id: int) -> None:
        """Transfer one card from one player to another."""
        # Get sender's inventory
        from_inventory_result = await self.db.exec(
            select(Inventory).where(
                Inventory.player_id == from_player_id, Inventory.card_id == card_id
            )
        )
        from_inventory = from_inventory_result.first()

        if not from_inventory or from_inventory.quantity < 1:
            msg = f"玩家 {from_player_id} 沒有卡片 {card_id}"
            raise HTTPException(status_code=400, detail=msg)

        # Decrease quantity for sender
        from_inventory.quantity -= 1
        self.db.add(from_inventory)

        # If quantity becomes 0, delete the inventory entry
        if from_inventory.quantity == 0:
            await self.db.delete(from_inventory)

        # Get receiver's inventory
        to_inventory_result = await self.db.exec(
            select(Inventory).where(
                Inventory.player_id == to_player_id, Inventory.card_id == card_id
            )
        )
        to_inventory = to_inventory_result.first()

        # Increase quantity for receiver (or create new inventory entry)
        if to_inventory:
            to_inventory.quantity += 1
            self.db.add(to_inventory)
        else:
            new_inventory = Inventory(player_id=to_player_id, card_id=card_id, quantity=1)
            self.db.add(new_inventory)

        # Commit the inventory changes first
        await self.db.commit()

        # Remove one instance of this card from sender's deck (if any)
        await self.deck_card_service.remove_card_instances_from_deck(
            player_id=from_player_id, card_id=card_id, quantity=1
        )

    async def _transfer_currency(self, from_player_id: int, to_player_id: int, amount: int) -> None:
        """Transfer currency from one player to another."""
        from_player = await self.player_service.get_player(from_player_id)
        to_player = await self.player_service.get_player(to_player_id)

        if not from_player or not to_player:
            msg = "找不到玩家"
            raise HTTPException(status_code=404, detail=msg)

        if from_player.currency < amount:
            msg = f"玩家 {from_player_id} 貨幣不足"
            raise HTTPException(status_code=400, detail=msg)

        from_player.currency -= amount
        to_player.currency += amount

        self.db.add(from_player)
        self.db.add(to_player)
