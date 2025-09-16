from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import json
import os
import datetime
import random
import string
import unicodedata
import re
import hashlib
from typing import Optional, Dict, List
from list import choose_random_word
from hangman_art import draw_progress_bar

app = FastAPI(title="Pendu Terminal API", version="1.0.0")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Game models
class GameStart(BaseModel):
    player_name: str
    password: str
    difficulty: str  # "easy", "middle", "hard"

class PlayerLogin(BaseModel):
    player_name: str
    password: str

class GameGuess(BaseModel):
    game_id: str
    guess: str
    hint_requested: bool = False

class GameResponse(BaseModel):
    game_id: str
    status: str  # "playing", "won", "lost"
    word_display: str
    wrong_letters: List[str]
    lives: int
    max_lives: int
    message: str
    progress_art: Optional[str] = None
    hints_used: int = 0
    game_time: Optional[float] = None
    secret_word: Optional[str] = None  # Le vrai mot pour les fins de partie

# In-memory game storage (en production, utilisez Redis ou une DB)
games = {}
STATS_FILE = "stats.json"
PLAYERS_FILE = "players.json"

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_stats(stats):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des stats: {e}")

def load_players():
    if not os.path.exists(PLAYERS_FILE):
        return {}
    try:
        with open(PLAYERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_players(players):
    try:
        with open(PLAYERS_FILE, "w", encoding="utf-8") as f:
            json.dump(players, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des joueurs: {e}")

def hash_password(password: str) -> str:
    """Hash le mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_player(player_name: str, password: str) -> bool:
    """Vérifie les identifiants d'un joueur"""
    players = load_players()
    if player_name not in players:
        return False
    return players[player_name]["password_hash"] == hash_password(password)

def register_player(player_name: str, password: str) -> bool:
    """Enregistre un nouveau joueur"""
    players = load_players()
    if player_name in players:
        return False

    players[player_name] = {
        "password_hash": hash_password(password),
        "created_at": datetime.datetime.now().isoformat(),
        "last_login": datetime.datetime.now().isoformat()
    }
    save_players(players)
    return True

def normalize_character(character):
    return unicodedata.normalize("NFD", character).encode("ascii", "ignore").decode("ascii")

def normalize_word(word):
    return "".join(normalize_character(c) for c in word)

def display_masked_word(word, found_letters):
    displayed_word = ""
    normalized_word = normalize_word(word.lower())

    for i, character in enumerate(word):
        if character.lower() in string.ascii_lowercase:
            if normalized_word[i] in found_letters:
                displayed_word += character
            else:
                displayed_word += "_"
        else:
            displayed_word += character

    return displayed_word

def word_is_complete(word, found_letters):
    normalized_word = normalize_word(word.lower())
    for character in normalized_word:
        if character in string.ascii_lowercase and character not in found_letters:
            return False
    return True

def get_hint(secret_word, found_letters):
    normalized_word = normalize_word(secret_word.lower())
    unfound_letters = []

    for i, char in enumerate(normalized_word):
        if char in string.ascii_lowercase and char not in found_letters:
            unfound_letters.append((char, secret_word[i]))

    if unfound_letters:
        normalized_hint, original_hint = random.choice(unfound_letters)
        return normalized_hint, original_hint
    return None, None

def validate_player_name(name: str) -> bool:
    """Valide le nom du joueur côté serveur"""
    if not name or len(name.strip()) < 2 or len(name.strip()) > 20:
        return False

    # Seuls lettres, chiffres et espaces autorisés
    if not re.match(r'^[a-zA-ZÀ-ÿ0-9\s]+$', name):
        return False

    # Éviter les noms avec seulement des espaces
    if len(name.strip()) < 2:
        return False

    # Liste de mots interdits
    forbidden_words = [
        'admin', 'root', 'system', 'null', 'undefined', 'anonymous',
        'merde', 'putain', 'connard', 'salaud', 'fdp', 'nazi', 'hitler'
    ]

    lower_name = name.lower()
    for forbidden in forbidden_words:
        if forbidden in lower_name:
            return False

    return True

def update_player_stats(player_name, won, word_length, wrong_letters_count, game_time, difficulty, hints_used=0, secret_word=""):
    stats = load_stats()

    if player_name not in stats:
        stats[player_name] = {
            "games_played": 0,
            "games_won": 0,
            "total_words_found": 0,
            "total_wrong_letters": 0,
            "total_time": 0,
            "best_time": None,
            "longest_word": 0,
            "difficulty_stats": {"easy": 0, "middle": 0, "hard": 0},
            "last_played": None,
            "current_streak": 0,
            "best_streak": 0,
            "difficulty_streaks": {"easy": 0, "middle": 0, "hard": 0},
            "best_difficulty_streaks": {"easy": 0, "middle": 0, "hard": 0},
            "achievements": [],
            "hints_used": 0,
            "words_history": {"won": [], "lost": []},
            "total_hints": 0
        }

    player_stats = stats[player_name]

    # Initialize new fields for existing players
    if "current_streak" not in player_stats:
        player_stats.update({
            "current_streak": 0,
            "best_streak": 0,
            "difficulty_streaks": {"easy": 0, "middle": 0, "hard": 0},
            "best_difficulty_streaks": {"easy": 0, "middle": 0, "hard": 0},
            "achievements": [],
            "hints_used": 0,
            "words_history": {"won": [], "lost": []},
            "total_hints": 0
        })

    player_stats["games_played"] += 1
    player_stats["total_wrong_letters"] += wrong_letters_count
    player_stats["total_time"] += game_time
    player_stats["total_hints"] += hints_used
    player_stats["last_played"] = datetime.datetime.now().isoformat()
    player_stats["last_game_perfect"] = (wrong_letters_count == 0 and won)

    difficulty_names = ["easy", "middle", "hard"]
    if 0 <= difficulty < len(difficulty_names):
        player_stats["difficulty_stats"][difficulty_names[difficulty]] += 1

    if won:
        player_stats["games_won"] += 1
        player_stats["total_words_found"] += 1
        player_stats["longest_word"] = max(player_stats["longest_word"], word_length)

        # Update streaks
        player_stats["current_streak"] += 1
        player_stats["best_streak"] = max(player_stats["best_streak"], player_stats["current_streak"])

        if secret_word:
            player_stats["words_history"]["won"].append({
                "word": secret_word,
                "date": datetime.datetime.now().isoformat(),
                "difficulty": difficulty_names[difficulty],
                "time": game_time,
                "hints_used": hints_used
            })

        if player_stats["best_time"] is None or game_time < player_stats["best_time"]:
            player_stats["best_time"] = game_time
    else:
        # Reset streaks on loss
        player_stats["current_streak"] = 0
        for diff in difficulty_names:
            player_stats["difficulty_streaks"][diff] = 0

        if secret_word:
            player_stats["words_history"]["lost"].append({
                "word": secret_word,
                "date": datetime.datetime.now().isoformat(),
                "difficulty": difficulty_names[difficulty],
                "time": game_time,
                "hints_used": hints_used
            })

    save_stats(stats)
    return player_stats

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/player/login")
async def login_player(login_data: PlayerLogin):
    """Connecte un joueur existant ou crée un nouveau compte"""
    # Validation du nom du joueur
    if not validate_player_name(login_data.player_name):
        raise HTTPException(
            status_code=400,
            detail="Nom invalide. Le nom doit contenir 2-20 caractères (lettres, chiffres, espaces uniquement) et ne pas contenir de mots interdits."
        )

    if len(login_data.password.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Le mot de passe doit contenir au moins 3 caractères."
        )

    players = load_players()
    stats = load_stats()

    # Si le joueur n'existe pas dans players mais existe dans stats (ancien compte)
    if login_data.player_name not in players and login_data.player_name in stats:
        if register_player(login_data.player_name, login_data.password):
            return {"status": "migrated", "message": f"Compte migré pour {login_data.player_name} ! Vos stats sont préservées."}
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la migration du compte")

    # Si le joueur n'existe nulle part, on le crée
    if login_data.player_name not in players:
        if register_player(login_data.player_name, login_data.password):
            return {"status": "registered", "message": f"Nouveau compte créé pour {login_data.player_name} !"}
        else:
            raise HTTPException(status_code=500, detail="Erreur lors de la création du compte")

    # Si le joueur existe, on vérifie le mot de passe
    if verify_player(login_data.player_name, login_data.password):
        # Mettre à jour la dernière connexion
        players[login_data.player_name]["last_login"] = datetime.datetime.now().isoformat()
        save_players(players)
        return {"status": "logged_in", "message": f"Bon retour {login_data.player_name} !"}
    else:
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")

@app.post("/api/game/start")
async def start_game(game_data: GameStart):
    # Validation du nom du joueur
    if not validate_player_name(game_data.player_name):
        raise HTTPException(
            status_code=400,
            detail="Nom invalide. Le nom doit contenir 2-20 caractères (lettres, chiffres, espaces uniquement) et ne pas contenir de mots interdits."
        )

    # Vérification de l'authentification
    if not verify_player(game_data.player_name, game_data.password):
        raise HTTPException(status_code=401, detail="Authentification requise")

    difficulty_map = {"easy": 0, "middle": 1, "hard": 2}
    max_errors_map = {"easy": 10, "middle": 6, "hard": 3}

    if game_data.difficulty not in difficulty_map:
        raise HTTPException(status_code=400, detail="Invalid difficulty")

    difficulty_level = difficulty_map[game_data.difficulty]
    secret_word = choose_random_word(difficulty_level)
    game_id = f"{game_data.player_name}_{datetime.datetime.now().timestamp()}"

    games[game_id] = {
        "player_name": game_data.player_name,
        "secret_word": secret_word,
        "secret_word_normalized": normalize_word(secret_word.lower()),
        "found_letters": set(),
        "wrong_letters": set(),
        "difficulty": difficulty_level,
        "difficulty_name": game_data.difficulty,
        "max_errors": max_errors_map[game_data.difficulty],
        "errors": 0,
        "hints_used": 0,
        "start_time": datetime.datetime.now().timestamp(),
        "status": "playing"
    }

    return GameResponse(
        game_id=game_id,
        status="playing",
        word_display=display_masked_word(secret_word, set()),
        wrong_letters=[],
        lives=max_errors_map[game_data.difficulty],
        max_lives=max_errors_map[game_data.difficulty],
        message=f"Nouveau jeu commencé ! Mot de {len(secret_word)} lettres (difficulté: {game_data.difficulty})",
        hints_used=0
    )

@app.post("/api/game/guess")
async def make_guess(guess_data: GameGuess):
    if guess_data.game_id not in games:
        raise HTTPException(status_code=404, detail="Game not found")

    game = games[guess_data.game_id]

    if game["status"] != "playing":
        raise HTTPException(status_code=400, detail="Game is finished")

    # Handle hint request
    if guess_data.hint_requested:
        if game["errors"] >= game["max_errors"] - 1:
            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["max_errors"] - game["errors"],
                max_lives=game["max_errors"],
                message="❌ Tu n'as pas assez de vies pour un indice !",
                hints_used=game["hints_used"]
            )

        hint_letter, original_letter = get_hint(game["secret_word"], game["found_letters"])
        if hint_letter:
            game["found_letters"].add(hint_letter)
            game["errors"] += 1
            game["hints_used"] += 1

            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["max_errors"] - game["errors"],
                max_lives=game["max_errors"],
                message=f"💡 INDICE: La lettre '{original_letter}' est dans le mot ! (coût: 1 vie)",
                hints_used=game["hints_used"]
            )

    guess = guess_data.guess.strip().lower()

    if not guess:
        return GameResponse(
            game_id=guess_data.game_id,
            status="playing",
            word_display=display_masked_word(game["secret_word"], game["found_letters"]),
            wrong_letters=list(game["wrong_letters"]),
            lives=game["max_errors"] - game["errors"],
            max_lives=game["max_errors"],
            message="Tu dois taper quelque chose !",
            hints_used=game["hints_used"]
        )

    # Single letter guess
    if len(guess) == 1:
        if not guess.isalpha():
            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["max_errors"] - game["errors"],
                max_lives=game["max_errors"],
                message="Merci d'entrer une lettre valide !",
                hints_used=game["hints_used"]
            )

        normalized_letter = normalize_character(guess)

        if normalized_letter in game["found_letters"] or normalized_letter in game["wrong_letters"]:
            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["max_errors"] - game["errors"],
                max_lives=game["max_errors"],
                message="Tu as déjà essayé cette lettre !",
                hints_used=game["hints_used"]
            )

        if normalized_letter in game["secret_word_normalized"]:
            game["found_letters"].add(normalized_letter)
            message = f"✓ Bonne lettre : {guess}"
        else:
            game["wrong_letters"].add(normalized_letter)
            game["errors"] += 1
            message = f"✗ Mauvaise lettre : {guess}"

    else:
        # Whole word guess
        guess_normalized = normalize_word(guess)
        if guess_normalized == game["secret_word_normalized"]:
            # Instant win
            game["status"] = "won"
            end_time = datetime.datetime.now().timestamp()
            game_time = end_time - game["start_time"]

            # Update stats
            player_stats = update_player_stats(
                game["player_name"], True, len(game["secret_word"]),
                len(game["wrong_letters"]), game_time, game["difficulty"],
                game["hints_used"], game["secret_word"]
            )

            return GameResponse(
                game_id=guess_data.game_id,
                status="won",
                word_display=game["secret_word"],
                wrong_letters=list(game["wrong_letters"]),
                lives=game["max_errors"] - game["errors"],
                max_lives=game["max_errors"],
                message=f"🎉 BRAVO ! Tu as trouvé le mot entier : {game['secret_word']} (Temps: {game_time:.1f}s)",
                hints_used=game["hints_used"],
                game_time=game_time,
                secret_word=game["secret_word"]
            )
        else:
            game["errors"] += 1
            message = f"✗ Mauvaise proposition de mot : \"{guess}\""

    # Check win condition
    if word_is_complete(game["secret_word"], game["found_letters"]):
        game["status"] = "won"
        end_time = datetime.datetime.now().timestamp()
        game_time = end_time - game["start_time"]

        # Update stats
        player_stats = update_player_stats(
            game["player_name"], True, len(game["secret_word"]),
            len(game["wrong_letters"]), game_time, game["difficulty"],
            game["hints_used"], game["secret_word"]
        )

        return GameResponse(
            game_id=guess_data.game_id,
            status="won",
            word_display=game["secret_word"],
            wrong_letters=list(game["wrong_letters"]),
            lives=game["max_errors"] - game["errors"],
            max_lives=game["max_errors"],
            message=f"🎉 BRAVO ! Tu as trouvé le mot : {game['secret_word']} (Temps: {game_time:.1f}s)",
            hints_used=game["hints_used"],
            game_time=game_time,
            secret_word=game["secret_word"]
        )

    # Check lose condition
    if game["errors"] >= game["max_errors"]:
        game["status"] = "lost"
        end_time = datetime.datetime.now().timestamp()
        game_time = end_time - game["start_time"]

        # Update stats
        player_stats = update_player_stats(
            game["player_name"], False, len(game["secret_word"]),
            len(game["wrong_letters"]), game_time, game["difficulty"],
            game["hints_used"], game["secret_word"]
        )

        progress_art = draw_progress_bar(game["errors"], game["max_errors"], game["difficulty"])

        return GameResponse(
            game_id=guess_data.game_id,
            status="lost",
            word_display=display_masked_word(game["secret_word"], game["found_letters"]),
            wrong_letters=list(game["wrong_letters"]),
            lives=0,
            max_lives=game["max_errors"],
            message=f"💀 PERDU ! Le mot était : {game['secret_word']} (Temps: {game_time:.1f}s)",
            progress_art=progress_art,
            hints_used=game["hints_used"],
            game_time=game_time,
            secret_word=game["secret_word"]
        )

    return GameResponse(
        game_id=guess_data.game_id,
        status="playing",
        word_display=display_masked_word(game["secret_word"], game["found_letters"]),
        wrong_letters=list(game["wrong_letters"]),
        lives=game["max_errors"] - game["errors"],
        max_lives=game["max_errors"],
        message=message,
        hints_used=game["hints_used"]
    )

@app.get("/api/stats/{player_name}")
async def get_player_stats(player_name: str):
    stats = load_stats()
    if player_name not in stats:
        raise HTTPException(status_code=404, detail="Player not found")
    return stats[player_name]

@app.get("/api/leaderboard")
async def get_leaderboard():
    stats = load_stats()
    if not stats:
        return {"players_by_wins": [], "players_by_winrate": [], "players_by_speed": []}

    # Sort players by different criteria
    players_by_wins = sorted(stats.items(), key=lambda x: x[1]["games_won"], reverse=True)[:5]
    players_by_winrate = sorted(
        [(name, data) for name, data in stats.items() if data["games_played"] >= 3],
        key=lambda x: x[1]["games_won"] / x[1]["games_played"] if x[1]["games_played"] > 0 else 0,
        reverse=True
    )[:5]
    players_by_speed = sorted(
        [(name, data) for name, data in stats.items() if data["best_time"] is not None],
        key=lambda x: x[1]["best_time"]
    )[:5]

    return {
        "players_by_wins": players_by_wins,
        "players_by_winrate": players_by_winrate,
        "players_by_speed": players_by_speed
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)