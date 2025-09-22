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
import redis
from typing import Optional, Dict, List
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()
from list import choose_random_word, DICTIONARIES
from hangman_art import draw_progress_bar

app = FastAPI(title="Pendu Terminal API", version="1.0.0")

# Redis connection
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Game models
class GameStart(BaseModel):
    player_name: str
    password: str
    difficulty: str
    language: str = "fr"  # Langue par défaut : français

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

# In-memory game storage
games = {}

# Redis keys
STATS_KEY = "pendu:stats"
PLAYERS_KEY = "pendu:players"

def load_stats():
    """Charge les statistiques depuis Redis"""
    try:
        data = redis_client.get(STATS_KEY)
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement des stats depuis Redis: {e}")
        return {}

def save_stats(stats):
    """Sauvegarde les statistiques dans Redis"""
    try:
        redis_client.set(STATS_KEY, json.dumps(stats, ensure_ascii=False))
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des stats dans Redis: {e}")

def load_players():
    """Charge les données des joueurs depuis Redis"""
    try:
        data = redis_client.get(PLAYERS_KEY)
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        print(f"Erreur lors du chargement des joueurs depuis Redis: {e}")
        return {}

def save_players(players):
    """Sauvegarde les données des joueurs dans Redis"""
    try:
        redis_client.set(PLAYERS_KEY, json.dumps(players, ensure_ascii=False))
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des joueurs dans Redis: {e}")

def migrate_json_to_redis():
    """Migre les données JSON existantes vers Redis si elles existent"""
    # Migrer les stats
    stats_file = "stats.json"
    if os.path.exists(stats_file):
        try:
            with open(stats_file, "r", encoding="utf-8") as f:
                stats_data = json.load(f)

            # Vérifier si les données n'existent pas déjà dans Redis
            if not redis_client.exists(STATS_KEY):
                save_stats(stats_data)
                print(f"✅ Migration des stats: {len(stats_data)} joueurs migrés vers Redis")
            else:
                print("⚠️ Stats déjà présentes dans Redis, migration ignorée")

        except Exception as e:
            print(f"❌ Erreur lors de la migration des stats: {e}")

    # Migrer les joueurs
    players_file = "players.json"
    if os.path.exists(players_file):
        try:
            with open(players_file, "r", encoding="utf-8") as f:
                players_data = json.load(f)

            # Vérifier si les données n'existent pas déjà dans Redis
            if not redis_client.exists(PLAYERS_KEY):
                save_players(players_data)
                print(f"✅ Migration des joueurs: {len(players_data)} comptes migrés vers Redis")
            else:
                print("⚠️ Joueurs déjà présents dans Redis, migration ignorée")

        except Exception as e:
            print(f"❌ Erreur lors de la migration des joueurs: {e}")

# Migration automatique au démarrage
try:
    # Test de connexion Redis
    redis_client.ping()
    print("✅ Connexion Redis établie")

    # Migration des données JSON existantes
    migrate_json_to_redis()

except Exception as e:
    print(f"❌ Erreur de connexion Redis: {e}")
    print("L'application ne pourra pas fonctionner sans Redis")

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

def update_player_stats(player_name, won, word_length, wrong_letters_count, game_time, difficulty, hints_used=0, secret_word="", infinite_stats=None, is_infinite_mode=False, language="fr"):
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
            "total_hints": 0,
            "infinite_mode_stats": {
                "games_played": 0,
                "best_words_found": 0,
                "total_words_found": 0,
                "average_words_found": 0.0,
                "max_lives_reached": 0,
                "total_lives_gained": 0,
                "best_session_time": None,
                "total_session_time": 0
            },
            "game_history": []
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

    # Initialize game_history for existing players
    if "game_history" not in player_stats:
        player_stats["game_history"] = []

    # Initialize infinite mode stats for existing players
    if "infinite_mode_stats" not in player_stats:
        player_stats["infinite_mode_stats"] = {
            "games_played": 0,
            "best_words_found": 0,
            "total_words_found": 0,
            "average_words_found": 0.0,
            "max_lives_reached": 0,
            "total_lives_gained": 0,
            "best_session_time": None,
            "total_session_time": 0
        }

    # Ne pas polluer les stats normales avec le mode infini (sauf pour les stats individuelles du mode infini)
    if not is_infinite_mode:
        player_stats["games_played"] += 1
        player_stats["total_wrong_letters"] += wrong_letters_count
        player_stats["total_time"] += game_time
    player_stats["total_hints"] += hints_used
    player_stats["last_played"] = datetime.datetime.now().isoformat()
    player_stats["last_game_perfect"] = (wrong_letters_count == 0 and won)

    difficulty_names = ["easy", "middle", "hard"]

    # Ne pas polluer les stats normales avec le mode infini
    if not is_infinite_mode:
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

    # Traitement des statistiques du mode infini
    if infinite_stats:
        infinite_mode_stats = player_stats["infinite_mode_stats"]

        # Si c'est la fin d'une session infinie (défaite)
        if not won and infinite_stats.get("is_end_of_session", False):
            infinite_mode_stats["games_played"] += 1
            words_found = infinite_stats.get("words_found", 0)
            lives_gained = infinite_stats.get("lives_gained", 0)
            max_lives = infinite_stats.get("max_lives", 0)
            session_time = infinite_stats.get("session_time", 0)

            # Meilleur nombre de mots trouvés
            infinite_mode_stats["best_words_found"] = max(infinite_mode_stats["best_words_found"], words_found)

            # Total de mots trouvés
            infinite_mode_stats["total_words_found"] += words_found

            # Calcul de la moyenne
            if infinite_mode_stats["games_played"] > 0:
                infinite_mode_stats["average_words_found"] = infinite_mode_stats["total_words_found"] / infinite_mode_stats["games_played"]

            # Maximum de vies atteint
            infinite_mode_stats["max_lives_reached"] = max(infinite_mode_stats["max_lives_reached"], max_lives)

            # Total de vies gagnées
            infinite_mode_stats["total_lives_gained"] += lives_gained

            # Meilleur temps de session
            if infinite_mode_stats["best_session_time"] is None or session_time > infinite_mode_stats["best_session_time"]:
                infinite_mode_stats["best_session_time"] = session_time

            # Temps total de session
            infinite_mode_stats["total_session_time"] += session_time

    # Enregistrer cette partie dans l'historique
    if not is_infinite_mode:  # Ne pas enregistrer les mots individuels du mode infini
        game_record = {
            "won": won,
            "word_length": word_length,
            "wrong_letters_count": wrong_letters_count,
            "game_time": game_time,
            "difficulty": difficulty,
            "hints_used": hints_used,
            "language": language,
            "secret_word": secret_word,
            "date": datetime.datetime.now().isoformat()
        }
        player_stats["game_history"].append(game_record)

    save_stats(stats)
    return player_stats

@app.get("/api/languages")
async def get_languages():
    """Retourne la liste des langues disponibles"""
    return {
        "languages": [
            {"code": code, "name": info["name"], "flag": info["flag"]}
            for code, info in DICTIONARIES.items()
        ]
    }

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

    # Valider la langue
    if game_data.language not in DICTIONARIES:
        raise HTTPException(status_code=400, detail="Invalid language")

    difficulty_level = difficulty_map[game_data.difficulty]
    secret_word = choose_random_word(difficulty_level, game_data.language)
    game_id = f"{game_data.player_name}_{datetime.datetime.now().timestamp()}"

    games[game_id] = {
        "player_name": game_data.player_name,
        "secret_word": secret_word,
        "secret_word_normalized": normalize_word(secret_word.lower()),
        "found_letters": set(),
        "wrong_letters": set(),
        "difficulty": difficulty_level,
        "difficulty_name": game_data.difficulty,
        "language": game_data.language,  # Ajouter la langue
        "max_errors": max_errors_map[game_data.difficulty],
        "lives": max_errors_map[game_data.difficulty],  # Nouvelle source de vérité
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
        message=f"Nouveau jeu commencé ! Mot de {len(secret_word)} lettres (difficulté: {game_data.difficulty}, langue: {DICTIONARIES[game_data.language]['name']})",
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
        if game["lives"] <= 1:  # Doit avoir au moins 1 vie après l'indice
            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["lives"],
                max_lives=game["max_errors"],
                message="❌ Tu n'as pas assez de vies pour un indice !",
                hints_used=game["hints_used"]
            )

        hint_letter, original_letter = get_hint(game["secret_word"], game["found_letters"])
        if hint_letter:
            game["found_letters"].add(hint_letter)
            game["lives"] -= 1  # Utiliser lives directement
            game["errors"] += 1  # Maintenir errors pour la cohérence
            game["hints_used"] += 1

            return GameResponse(
                game_id=guess_data.game_id,
                status="playing",
                word_display=display_masked_word(game["secret_word"], game["found_letters"]),
                wrong_letters=list(game["wrong_letters"]),
                lives=game["lives"],
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
            lives=game["lives"],
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
                lives=game["lives"],
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
                lives=game["lives"],
                max_lives=game["max_errors"],
                message="Tu as déjà essayé cette lettre !",
                hints_used=game["hints_used"]
            )

        if normalized_letter in game["secret_word_normalized"]:
            game["found_letters"].add(normalized_letter)
            message = f"✓ Bonne lettre : {guess}"
        else:
            game["wrong_letters"].add(normalized_letter)
            game["lives"] -= 1  # Décrémenter les vies directement
            game["errors"] += 1  # Maintenir errors pour la cohérence
            message = f"✗ Mauvaise lettre : {guess}"

            # VÉRIFICATION IMMÉDIATE DES VIES APRÈS ERREUR
            if game["lives"] <= 0:
                game["status"] = "lost"
                end_time = datetime.datetime.now().timestamp()
                game_time = end_time - game["start_time"]

                # Update stats
                player_stats = update_player_stats(
                    game["player_name"], False, len(game["secret_word"]),
                    len(game["wrong_letters"]), game_time, game["difficulty"],
                    game["hints_used"], game["secret_word"], None, False, game.get("language", "fr")
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
                game["hints_used"], game["secret_word"], None, False, game.get("language", "fr")
            )

            return GameResponse(
                game_id=guess_data.game_id,
                status="won",
                word_display=game["secret_word"],
                wrong_letters=list(game["wrong_letters"]),
                lives=game["lives"],
                max_lives=game["max_errors"],
                message=f"🎉 BRAVO ! Tu as trouvé le mot entier : {game['secret_word']} (Temps: {game_time:.1f}s)",
                hints_used=game["hints_used"],
                game_time=game_time,
                secret_word=game["secret_word"]
            )
        else:
            game["lives"] -= 1  # Décrémenter les vies directement
            game["errors"] += 1  # Maintenir errors pour la cohérence
            message = f"✗ Mauvaise proposition de mot : \"{guess}\""

            # VÉRIFICATION IMMÉDIATE DES VIES APRÈS ERREUR DE MOT
            if game["lives"] <= 0:
                game["status"] = "lost"
                end_time = datetime.datetime.now().timestamp()
                game_time = end_time - game["start_time"]

                # Update stats
                player_stats = update_player_stats(
                    game["player_name"], False, len(game["secret_word"]),
                    len(game["wrong_letters"]), game_time, game["difficulty"],
                    game["hints_used"], game["secret_word"], None, False, game.get("language", "fr")
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
            lives=game["lives"],
            max_lives=game["max_errors"],
            message=f"🎉 BRAVO ! Tu as trouvé le mot : {game['secret_word']} (Temps: {game_time:.1f}s)",
            hints_used=game["hints_used"],
            game_time=game_time,
            secret_word=game["secret_word"]
        )

    # Check lose condition (cette vérification ne devrait normalement plus être nécessaire)
    if game["lives"] <= 0:
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
        lives=game["lives"],
        max_lives=game["max_errors"],
        message=message,
        hints_used=game["hints_used"]
    )

@app.get("/api/stats/{player_name}")
async def get_player_stats(player_name: str, language: str = None):
    stats = load_stats()
    if player_name not in stats:
        raise HTTPException(status_code=404, detail="Player not found")

    player_stats = stats[player_name]

    # Si aucune langue spécifiée, retourner toutes les stats
    if not language:
        return player_stats

    # Filtrer par langue si spécifiée
    filtered_stats = {
        "games_played": 0,
        "games_won": 0,
        "total_words_found": 0,
        "total_wrong_letters": 0,
        "total_time": 0,
        "best_time": None,
        "longest_word": 0,
        "current_streak": 0,
        "best_streak": 0,
        "total_hints": 0,
        "difficulty_stats": {},
        "infinite_mode_stats": {
            "games_played": 0,
            "best_words_found": 0,
            "average_words_found": 0,
            "max_lives_reached": 0,
            "total_lives_gained": 0,
            "best_session_time": None,
            "total_session_time": 0
        }
    }

    # Parcourir l'historique des parties pour filtrer par langue
    game_history = player_stats.get("game_history", [])
    language_games = [game for game in game_history if game.get("language") == language]

    if not language_games:
        return filtered_stats

    # Calculer les stats pour cette langue
    total_time = 0
    best_time = None
    won_games = 0
    total_words = 0
    total_wrong = 0
    total_hints = 0
    longest_word = 0
    difficulty_counts = {}

    for game in language_games:
        total_time += game.get("game_time", 0)
        total_words += 1 if game.get("won") else 0
        total_wrong += game.get("wrong_letters_count", 0)
        total_hints += game.get("hints_used", 0)

        if game.get("won"):
            won_games += 1
            game_time = game.get("game_time", 0)
            if best_time is None or game_time < best_time:
                best_time = game_time

        word_length = game.get("word_length", 0)
        if word_length > longest_word:
            longest_word = word_length

        difficulty = game.get("difficulty", "unknown")
        difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

    filtered_stats.update({
        "games_played": len(language_games),
        "games_won": won_games,
        "total_words_found": total_words,
        "total_wrong_letters": total_wrong,
        "total_time": total_time,
        "best_time": best_time,
        "longest_word": longest_word,
        "total_hints": total_hints,
        "difficulty_stats": difficulty_counts
    })

    # Pour les stats du mode infini, on garde les stats globales car elles ne sont pas encore stockées par langue
    if "infinite_mode_stats" in player_stats:
        filtered_stats["infinite_mode_stats"] = player_stats["infinite_mode_stats"]

    return filtered_stats

@app.post("/api/infinite/stats")
async def update_infinite_stats(infinite_data: dict):
    """Enregistre les statistiques de fin de session en mode infini"""
    player_name = infinite_data.get("player_name")
    password = infinite_data.get("password")

    # Vérification de l'authentification
    if not verify_player(player_name, password):
        raise HTTPException(status_code=401, detail="Authentification requise")

    # Préparer les stats du mode infini
    infinite_stats = {
        "is_end_of_session": True,
        "words_found": infinite_data.get("words_found", 0),
        "lives_gained": infinite_data.get("lives_gained", 0),
        "max_lives": infinite_data.get("max_lives", 0),
        "session_time": infinite_data.get("session_time", 0)
    }

    # Mettre à jour les stats avec des valeurs factices pour le mot final
    update_player_stats(
        player_name=player_name,
        won=False,  # Défaite en mode infini
        word_length=1,  # Pas important pour les stats infini
        wrong_letters_count=0,  # Pas important pour les stats infini
        game_time=0,  # Pas important pour les stats infini
        difficulty=0,  # Pas important pour les stats infini
        infinite_stats=infinite_stats,
        is_infinite_mode=True,
        language="fr"  # Pour le mode infini, langue par défaut
    )

    return {"status": "success", "message": "Statistiques du mode infini enregistrées"}

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