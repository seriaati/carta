import json
from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI
from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings
from app.core.db import get_db
from app.core.enums import PvPMode
from app.models.card import Card
from app.models.deck_card import DeckCard
from app.schemas.pvp_battle import BattleResult, CardBattleInfo, PlayerBattleInfo
from app.services.settings import SettingsService

# Rarity value mapping for the battle system
RARITY_VALUES = {"C": 1, "R": 2, "SR": 3, "SSR": 4, "UR": 5, "LR": 6, "EX": 7}


class PvPBattleService:
    """Service for executing PvP battles using AI."""

    def __init__(
        self,
        db: Annotated[AsyncSession, Depends(get_db)],
        settings_service: Annotated[SettingsService, Depends()],
    ) -> None:
        self.db = db
        self.settings_service = settings_service
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)

    async def _get_player_deck_cards(self, player_id: int) -> list[Card]:
        """Get all cards in a player's deck with full card info."""
        result = await self.db.exec(
            select(Card)
            .join(DeckCard, col(DeckCard.card_id) == Card.id)
            .where(DeckCard.player_id == player_id)
            .order_by(col(DeckCard.position))
        )
        return list(result.all())

    def _format_card_for_battle(self, card: Card) -> CardBattleInfo:
        """Convert a Card model to minimal battle info for token efficiency."""
        return CardBattleInfo(
            name=card.name,
            rarity=card.rarity.value,
            attack=card.attack or 0,
            defense=card.defense or 0,
            ability=card.description,
        )

    def _format_cards_compact(self, player: PlayerBattleInfo) -> str:
        """Format player cards in a compact way to save tokens."""
        lines = [
            f"- {c.name}|{c.rarity}|ATK:{c.attack}|DEF:{c.defense}|{c.ability}"
            for c in player.cards
        ]
        return "\n".join(lines)

    async def execute_battle(
        self,
        challenger_id: int,
        opponent_id: int,
        mode: PvPMode = PvPMode.FRIENDLY,
        bet_amount: int = 0,
    ) -> BattleResult:
        """Execute a PvP battle between two players using AI.

        If mode is RANKED, automatically updates ranking scores after battle.
        If mode is DUEL, automatically processes bet transfer after battle.
        """
        # Get deck cards for both players
        challenger_cards = await self._get_player_deck_cards(challenger_id)
        opponent_cards = await self._get_player_deck_cards(opponent_id)

        # Prepare battle info
        challenger_info = PlayerBattleInfo(
            player_id=challenger_id,
            cards=[self._format_card_for_battle(c) for c in challenger_cards],
        )
        opponent_info = PlayerBattleInfo(
            player_id=opponent_id, cards=[self._format_card_for_battle(c) for c in opponent_cards]
        )

        # Get the system prompt from settings
        system_prompt = await self.settings_service.get_prompt()
        if not system_prompt:
            system_prompt = "You are a card battle judge. Determine the winner based on card stats."

        # Build the user message with battle data
        user_message = self._build_battle_message(challenger_info, opponent_info)

        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Low temperature for consistent results
            max_tokens=1000,
        )

        # Parse the response
        content = response.choices[0].message.content
        if not content:
            msg = "Empty response from AI"
            raise ValueError(msg)

        result_data = json.loads(content)

        # Determine winner ID from response
        winner_key = result_data.get("winner", "").lower()
        if "attacker" in winner_key or "challenger" in winner_key or winner_key == "a":
            winner_id = challenger_id
        elif "defender" in winner_key or "opponent" in winner_key or winner_key == "b":
            winner_id = opponent_id
        else:
            # Try to parse winner directly if it's a player ID
            try:
                winner_id = int(result_data.get("winner_id", challenger_id))
            except (ValueError, TypeError):
                winner_id = challenger_id

        # Update ranking scores if this is a ranked battle
        if mode == PvPMode.RANKED:
            from app.services.pvp_rank import PvPRankService  # noqa: PLC0415

            rank_service = PvPRankService(db=self.db)
            loser_id = opponent_id if winner_id == challenger_id else challenger_id
            await rank_service.update_scores_after_battle(winner_id, loser_id)

        # Process bet if this is a duel
        if mode == PvPMode.DUEL and bet_amount > 0:
            from app.services.pvp_rank import PvPRankService  # noqa: PLC0415

            rank_service = PvPRankService(db=self.db)
            loser_id = opponent_id if winner_id == challenger_id else challenger_id
            await rank_service.process_duel_bet(winner_id, loser_id, bet_amount)

        return BattleResult(
            winner_id=winner_id,
            battle_narrative=result_data.get("narrative", result_data.get("battle_narrative", "")),
        )

    def _build_battle_message(
        self, challenger: PlayerBattleInfo, opponent: PlayerBattleInfo
    ) -> str:
        """Build a token-efficient battle request message."""
        return f"""【對戰請求】
攻擊方(A) ID:{challenger.player_id}
{self._format_cards_compact(challenger)}

防守方(B) ID:{opponent.player_id}
{self._format_cards_compact(opponent)}

請依規則判定勝負,以JSON格式回應:
{{"winner": "A或B", "narrative": "戰鬥敘述(含數值計算過程)"}}"""
