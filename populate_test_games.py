"""
Скрипт для заповнення бази тестовими настільними іграми
"""
import asyncio
from database import init_db, get_session
from services import GameService


# Список тестових ігор
TEST_GAMES = [
    {
        "name": "Катан",
        "description": "Економічна стратегія про колонізацію острова. Будуйте поселення, торгуйте ресурсами та розвивайте свою цивілізацію.",
        "min_players": 3,
        "max_players": 4,
        "avg_duration": 90
    },
    {
        "name": "Каркассон",
        "description": "Стратегічна гра про будівництво середньовічного французького міста за допомогою тайлів. Розміщуйте своїх міплів і набирайте очки.",
        "min_players": 2,
        "max_players": 5,
        "avg_duration": 45
    },
    {
        "name": "Пандемія",
        "description": "Кооперативна гра, де команда лікарів бореться проти чотирьох смертельних хвороб. Працюйте разом, щоб врятувати людство!",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 60
    },
    {
        "name": "7 Чудес",
        "description": "Швидка стратегічна гра про розвиток стародавніх цивілізацій. Будуйте чудеса світу та розвивайте свою цивілізацію.",
        "min_players": 3,
        "max_players": 7,
        "avg_duration": 30
    },
    {
        "name": "Terraforming Mars",
        "description": "Космічна стратегія про тераформування Марса. Керуйте корпорацією, підвищуйте температуру та створюйте океани.",
        "min_players": 1,
        "max_players": 5,
        "avg_duration": 120
    },
    {
        "name": "Азул",
        "description": "Елегантна абстрактна гра про створення мозаїки для королівського палацу. Збирайте плитки і створюйте візерунки.",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 45
    },
    {
        "name": "Codenames",
        "description": "Командна словесна гра, де капітани дають підказки, щоб допомогти своїй команді знайти правильні слова.",
        "min_players": 4,
        "max_players": 8,
        "avg_duration": 20
    },
    {
        "name": "Ticket to Ride",
        "description": "Сімейна гра про будівництво залізничних маршрутів через всю країну. З'єднуйте міста і виконуйте завдання.",
        "min_players": 2,
        "max_players": 5,
        "avg_duration": 60
    },
    {
        "name": "Диксіт",
        "description": "Креативна гра з красивими картками. Вигадуйте асоціації та вгадуйте, яку картку описав оповідач.",
        "min_players": 3,
        "max_players": 6,
        "avg_duration": 30
    },
    {
        "name": "Splendor",
        "description": "Гра про ренесансних купців та торгівлю самоцвітами. Збирайте ресурси та розвивайте свою торгову імперію.",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 30
    },
    {
        "name": "Wingspan",
        "description": "Красива гра про птахів та орнітологію. Залучайте птахів до свого заповідника та збирайте очки.",
        "min_players": 1,
        "max_players": 5,
        "avg_duration": 60
    },
    {
        "name": "King of Tokyo",
        "description": "Динамічна гра про гігантських монстрів, які б'ються за контроль над Токіо. Кидайте кубики та атакуйте противників!",
        "min_players": 2,
        "max_players": 6,
        "avg_duration": 30
    },
    {
        "name": "Сумерки Імперії",
        "description": "Епічна космічна 4X стратегія. Керуйте інопланетною расою, завойовуйте галактику та ведіть дипломатію.",
        "min_players": 3,
        "max_players": 6,
        "avg_duration": 240
    },
    {
        "name": "Dominion",
        "description": "Класична гра в жанрі deck-building. Будуйте свою колоду карт та розширюйте свої володіння.",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 45
    },
    {
        "name": "Brass Birmingham",
        "description": "Економічна гра про промислову революцію в Англії. Будуйте заводи, створюйте торгові мережі.",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 120
    },
    {
        "name": "Root",
        "description": "Асиметрична військова гра в лісовому фентезійному світі. Кожна фракція має унікальні правила та цілі.",
        "min_players": 2,
        "max_players": 4,
        "avg_duration": 90
    },
    {
        "name": "Scythe",
        "description": "Стратегія в альтернативній історії 1920-х років. Керуйте фракцією, розвивайте економіку та боріться за контроль.",
        "min_players": 1,
        "max_players": 5,
        "avg_duration": 115
    }
]


async def populate_games():
    """Заповнити базу тестовими іграми"""
    print("🎮 Початок заповнення бази тестовими іграми...")
    
    # Ініціалізуємо базу
    await init_db()
    print("✅ База даних ініціалізована")
    
    # Додаємо кожну гру
    async for session in get_session():
        added_count = 0
        
        for game_data in TEST_GAMES:
            try:
                game = await GameService.create_new_game(
                    session=session,
                    name=game_data["name"],
                    description=game_data["description"],
                    min_players=game_data["min_players"],
                    max_players=game_data["max_players"],
                    avg_duration=game_data["avg_duration"],
                    image_path=None  # Без зображень
                )
                added_count += 1
                print(f"  ✓ Додано: {game.name}")
            except Exception as e:
                print(f"  ✗ Помилка при додаванні {game_data['name']}: {e}")
        
        print(f"\n🎉 Успішно додано {added_count} з {len(TEST_GAMES)} ігор!")
        
        # Показуємо статистику
        games = await GameService.get_all_active_games(session)
        print(f"📊 Всього ігор в базі: {len(games)}")


if __name__ == "__main__":
    asyncio.run(populate_games())

