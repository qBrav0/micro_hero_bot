from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Game
from database.crud import (
    create_game, get_game, get_all_games, 
    update_game, delete_game
)


class GameService:
    """Сервіс для роботи з іграми"""
    
    @staticmethod
    async def create_new_game(
        session: AsyncSession,
        name: str,
        description: str,
        min_players: int,
        max_players: int,
        avg_duration: int,
        image_file_id: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Game:
        """Створити нову гру"""
        return await create_game(
            session=session,
            name=name,
            description=description,
            min_players=min_players,
            max_players=max_players,
            avg_duration=avg_duration,
            image_file_id=image_file_id,
            image_path=image_path
        )
    
    @staticmethod
    async def get_game_by_id(session: AsyncSession, game_id: int, active_only: bool = True) -> Optional[Game]:
        """Отримати гру за ID"""
        return await get_game(session, game_id, active_only=active_only)
    
    @staticmethod
    async def get_all_active_games(session: AsyncSession) -> List[Game]:
        """Отримати всі активні ігри"""
        return await get_all_games(session, active_only=True)
    
    @staticmethod
    async def update_game_info(
        session: AsyncSession,
        game: Game,
        **kwargs
    ) -> Game:
        """Оновити інформацію про гру"""
        for key, value in kwargs.items():
            if hasattr(game, key):
                setattr(game, key, value)
        
        return await update_game(session, game)
    
    @staticmethod
    async def deactivate_game(session: AsyncSession, game_id: int) -> bool:
        """Деактивувати гру"""
        return await delete_game(session, game_id)
    
    @staticmethod
    def format_game_info(game: Game) -> str:
        """Форматувати інформацію про гру для відображення"""
        info = f"🎮 <b>{game.name}</b>\n\n"
        info += f"📝 <b>Опис:</b>\n{game.description}\n\n"
        info += f"👥 <b>Кількість гравців:</b> {game.min_players}-{game.max_players}\n"
        info += f"⏱️ <b>Середня тривалість:</b> {game.avg_duration} хв\n"
        
        return info
