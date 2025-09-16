import string
import unicodedata
import threading
import time
import json
import datetime
import os
import sys
from list import choose_random_word
from hangman_art import draw_hangman, draw_progress_bar
import random

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
MAGENTA = "\033[35m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_RED = "\033[91m"
BRIGHT_YELLOW = "\033[93m"
RESET = "\033[0m"

STATS_FILE = "stats.json"

def clear_screen():
    print("\033[2J\033[H", end="")

def load_stats():
    if not os.path.exists(STATS_FILE):
        return {}

    try:
        with open(STATS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_stats(stats):
    """Save player statistics to file"""
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des stats: {e}")

def update_player_stats(player_name, won, word_length, wrong_letters_count, game_time, difficulty, hints_used=0, secret_word=""):
    """Update statistics for a player"""
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

    # Ensure integer values for compatibility
    for key in ["games_played", "games_won", "total_words_found", "total_wrong_letters", "longest_word"]:
        if key in player_stats and isinstance(player_stats[key], float):
            player_stats[key] = int(player_stats[key])

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

        # Update difficulty streaks
        diff_name = difficulty_names[difficulty]
        player_stats["difficulty_streaks"][diff_name] += 1
        player_stats["best_difficulty_streaks"][diff_name] = max(
            player_stats["best_difficulty_streaks"][diff_name],
            player_stats["difficulty_streaks"][diff_name]
        )

        # Add word to history
        if secret_word:
            player_stats["words_history"]["won"].append({
                "word": secret_word,
                "date": datetime.datetime.now().isoformat(),
                "difficulty": diff_name,
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

        # Add word to lost history
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

def get_key():
    """Get a single keypress without Enter"""
    try:
        import msvcrt
        key = msvcrt.getch()
        if key == b"\xe0":  # Arrow keys on Windows
            key = msvcrt.getch()
            if key == b"H":  # Up arrow
                return "up"
            elif key == b"P":  # Down arrow
                return "down"
        elif key == b"\r":  # Enter
            return "enter"
        elif key == b"\x1b":  # Escape
            return "escape"
        return key.decode("utf-8", errors="ignore")
    except ImportError:
        # Fallback for non-Windows systems
        import termios, tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            if key == "\x1b":  # Escape sequence
                key += sys.stdin.read(2)
                if key == "\x1b[A":  # Up arrow
                    return "up"
                elif key == "\x1b[B":  # Down arrow
                    return "down"
            elif key == "\r" or key == "\n":  # Enter
                return "enter"
            return key
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def show_menu():
    """Display interactive menu with arrow navigation"""
    menu_options = [
        ("🎮  Jouer", "play"),
        ("📊  Statistiques", "stats"),
        ("🏆  Leaderboard", "leaderboard"),
        ("❌  Quitter", "quit")
    ]

    selected = 0

    while True:
        clear_screen()
        print(f"{YELLOW}═══════════════════════════════════════{RESET}")
        print(f"{YELLOW}            JEU DU PENDU           {RESET}")
        print(f"{YELLOW}═══════════════════════════════════════{RESET}\n")

        for i, (option_text, _) in enumerate(menu_options):
            if i == selected:
                print(f"{GREEN}► {option_text} ◄{RESET}")
            else:
                print(f"  {option_text}")

        print(f"\n{YELLOW}Utilisez les flèches ↑↓ pour naviguer, Entrée pour sélectionner{RESET}")

        key = get_key()

        if key == "up":
            selected = (selected - 1) % len(menu_options)
        elif key == "down":
            selected = (selected + 1) % len(menu_options)
        elif key == "enter":
            return menu_options[selected][1]
        elif key == "escape":
            return "quit"

def show_player_stats(player_name):
    """Display detailed statistics for a player"""
    stats = load_stats()

    if player_name not in stats:
        print(f"Aucune statistique trouvée pour {player_name}")
        input("Appuyez sur Entrée pour continuer...")
        return

    player_stats = stats[player_name]
    clear_screen()

    print(f"{BLUE}═══════════════════════════════════════{RESET}")
    print(f"{BLUE}       STATISTIQUES DE {player_name.upper()}       {RESET}")
    print(f"{BLUE}═══════════════════════════════════════{RESET}\n")

    print(f"🎮  Parties jouées: {player_stats['games_played']}")
    print(f"🏆  Parties gagnées: {player_stats['games_won']}")

    if player_stats["games_played"] > 0:
        win_rate = (player_stats["games_won"] / player_stats["games_played"]) * 100
        print(f"📈  Taux de réussite: {win_rate:.1f}%")

    print(f"📝  Mots trouvés: {player_stats['total_words_found']}")
    print(f"❌  Lettres fausses totales: {player_stats['total_wrong_letters']}")

    if player_stats["total_time"] > 0:
        avg_time = player_stats["total_time"] / player_stats["games_played"]
        print(f"⏱️  Temps moyen par partie: {avg_time:.1f}s")

        if player_stats["total_words_found"] > 0:
            words_per_minute = player_stats["total_words_found"] / (player_stats["total_time"] / 60)
            print(f"🚀  Mots par minute: {words_per_minute:.2f}")

    if player_stats["best_time"]:
        print(f"⚡  Meilleur temps: {player_stats['best_time']:.1f}s")

    print(f"📏  Mot le plus long trouvé: {player_stats['longest_word']} lettres")

    # Streaks and achievements
    if "current_streak" in player_stats:
        print(f"🔥  Série actuelle: {player_stats['current_streak']}")
        print(f"🏆  Meilleure série: {player_stats['best_streak']}")
        print(f"💡  Indices utilisés: {player_stats.get('total_hints', 0)}")

    print(f"\n{YELLOW}Répartition par difficulté:{RESET}")
    for diff, count in player_stats["difficulty_stats"].items():
        streak_info = ""
        if "difficulty_streaks" in player_stats:
            current_streak = player_stats["difficulty_streaks"][diff]
            best_streak = player_stats["best_difficulty_streaks"][diff]
            if current_streak > 0:
                streak_info = f" (série: {current_streak})"
            elif best_streak > 0:
                streak_info = f" (record: {best_streak})"
        print(f"  {diff.capitalize()}: {count} parties{streak_info}")

    # Achievements
    if "achievements" in player_stats and player_stats["achievements"]:
        print(f"\n{BRIGHT_YELLOW}🏆 Succès débloqués: {len(player_stats['achievements'])}{RESET}")
        for achievement in player_stats["achievements"]:
            print(f"  ✓ {achievement}")

    # Recent words history
    if "words_history" in player_stats:
        recent_won = player_stats["words_history"]["won"][-5:]
        recent_lost = player_stats["words_history"]["lost"][-5:]

        if recent_won:
            print(f"\n{GREEN}🎯 Derniers mots trouvés:{RESET}")
            for word_info in reversed(recent_won):
                print(f"  ✓ {word_info['word']} ({word_info['difficulty']}, {word_info['time']:.1f}s)")

        if recent_lost:
            print(f"\n{RED}❌ Derniers mots ratés:{RESET}")
            for word_info in reversed(recent_lost):
                print(f"  ✗ {word_info['word']} ({word_info['difficulty']}, {word_info['time']:.1f}s)")

    if player_stats["last_played"]:
        last_played = datetime.datetime.fromisoformat(player_stats["last_played"])
        print(f"\n🕒  Dernière partie: {last_played.strftime('%d/%m/%Y à %H:%M')}")

    input(f"\n{GREEN}Appuyez sur Entrée pour retourner au menu...{RESET}")

def show_leaderboard():
    """Display the leaderboard of all players"""
    stats = load_stats()

    if not stats:
        clear_screen()
        print(f"{RED}Aucune statistique disponible{RESET}")
        input("Appuyez sur Entrée pour continuer...")
        return

    # Sort players by different criteria
    players_by_wins = sorted(stats.items(), key=lambda x: x[1]["games_won"], reverse=True)
    players_by_winrate = sorted(
        [(name, data) for name, data in stats.items() if data["games_played"] >= 3],
        key=lambda x: x[1]["games_won"] / x[1]["games_played"] if x[1]["games_played"] > 0 else 0,
        reverse=True
    )
    players_by_speed = sorted(
        [(name, data) for name, data in stats.items() if data["best_time"] is not None],
        key=lambda x: x[1]["best_time"]
    )

    clear_screen()
    print(f"{YELLOW}═══════════════════════════════════════{RESET}")
    print(f"{YELLOW}            LEADERBOARD            {RESET}")
    print(f"{YELLOW}═══════════════════════════════════════{RESET}\n")

    # Top wins
    print(f"{GREEN}🏆  Top Victoires:{RESET}")
    for i, (name, data) in enumerate(players_by_wins[:5], 1):
        print(f"{i}. {name}: {data['games_won']} victoires")

    # Top win rate (min 3 games)
    if players_by_winrate:
        print(f"\n{BLUE}📈  Meilleur taux de réussite (min 3 parties):{RESET}")
        for i, (name, data) in enumerate(players_by_winrate[:5], 1):
            rate = (data["games_won"] / data["games_played"]) * 100
            print(f"{i}. {name}: {rate:.1f}% ({data['games_won']}/{data['games_played']})")

    # Fastest players
    if players_by_speed:
        print(f"\n{CYAN}⚡  Plus rapides:{RESET}")
        for i, (name, data) in enumerate(players_by_speed[:5], 1):
            print(f"{i}. {name}: {data['best_time']:.1f}s")

    input(f"\n{GREEN}Appuyez sur Entrée pour retourner au menu...{RESET}")

def get_input_with_timer(prompt, timeout=10, game_state=None):
    """Get input with a visible countdown timer that updates the game display"""
    input_result = [None]

    def get_input():
        try:
            input_result[0] = input().strip().lower()
        except:
            pass

    input_thread = threading.Thread(target=get_input)
    input_thread.daemon = True
    input_thread.start()

    for remaining in range(timeout, 0, -1):
        if game_state:
            clear_screen()
            print(" ")
            print(f"Mot : {game_state['word_display']}")

            if game_state['wrong_letters'] and game_state['difficulty'] == 0:
                print("Lettres fausses : " + ", ".join(sorted(game_state['wrong_letters'])))

            lives_display = f"Vies restantes : {(RED + '♥ ' + RESET) * game_state['lives']}"
            if remaining <= 5:  # Red = <= 5 seconds
                lives_display += f" ({RED}⏰ {remaining}s{RESET})"
            else:
                lives_display += f" ({GREEN}⏰ {remaining}s{RESET})"
            print(lives_display)
            print(f"\n{prompt}", end="", flush=True)

        for _ in range(10):  # Check 10 times per second
            if input_result[0] is not None:
                return input_result[0]
            time.sleep(0.1)  # Sleep for 100ms each time

    if input_result[0] is not None:
        return input_result[0]

    if game_state:
        clear_screen()
        print(f"Mot : {game_state['word_display']}")
        if game_state['wrong_letters'] and game_state['difficulty'] == 0:
            print("Lettres fausses : " + ", ".join(sorted(game_state['wrong_letters'])))
        print(f"Vies restantes : {(RED + '♥ ' + RESET) * game_state['lives']}")
        print(f"\n⏰  Temps écoulé ! Tu perds une vie.")

    return None

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

def is_valid_letter(entry):
    return len(entry) == 1 and entry.isalpha()

def word_is_complete(word, found_letters):
    """Check if all letters of the word have been found"""
    normalized_word = normalize_word(word.lower())
    for character in normalized_word:
        if character in string.ascii_lowercase and character not in found_letters:
            return False
    return True

def show_loading_animation(message, duration=1):
    """Show a loading animation"""
    chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for i in range(int(duration * 10)):
        print(f"\r{YELLOW}{chars[i % len(chars)]} {message}...{RESET}", end="", flush=True)
        time.sleep(0.1)
    print(f"\r{' ' * (len(message) + 10)}\r", end="", flush=True)

def get_hint(secret_word, found_letters):
    """Get a random unfound letter as hint"""
    normalized_word = normalize_word(secret_word.lower())
    unfound_letters = []

    for i, char in enumerate(normalized_word):
        if char in string.ascii_lowercase and char not in found_letters:
            unfound_letters.append((char, secret_word[i]))

    if unfound_letters:
        normalized_hint, original_hint = random.choice(unfound_letters)
        return normalized_hint, original_hint
    return None, None

def check_achievements(player_stats, difficulty_names):
    """Check and award new achievements"""
    new_achievements = []

    # Streak achievements
    if player_stats['current_streak'] == 5 and 'streak_5' not in player_stats['achievements']:
        new_achievements.append('streak_5')
        player_stats['achievements'].append('streak_5')

    if player_stats['current_streak'] == 10 and 'streak_10' not in player_stats['achievements']:
        new_achievements.append('streak_10')
        player_stats['achievements'].append('streak_10')

    # Difficulty streak achievements
    for i, diff in enumerate(difficulty_names):
        if player_stats['difficulty_streaks'][diff] == 3 and f'{diff}_streak_3' not in player_stats['achievements']:
            new_achievements.append(f'{diff}_streak_3')
            player_stats['achievements'].append(f'{diff}_streak_3')

    # Games played achievements
    if player_stats['games_played'] == 50 and 'games_50' not in player_stats['achievements']:
        new_achievements.append('games_50')
        player_stats['achievements'].append('games_50')

    # Perfect game (no wrong letters)
    if player_stats.get('last_game_perfect', False) and 'perfect_game' not in player_stats['achievements']:
        new_achievements.append('perfect_game')
        player_stats['achievements'].append('perfect_game')

    return new_achievements

def display_achievements(achievements):
    """Display achievement notifications"""
    achievement_messages = {
        'streak_5': '🔥 Série de 5 victoires !',
        'streak_10': '🔥🔥 Série de 10 victoires !',
        'easy_streak_3': '🟢 3 victoires d\'affilée en Facile !',
        'middle_streak_3': '🟡 3 victoires d\'affilée en Moyen !',
        'hard_streak_3': '🔴 3 victoires d\'affilée en Difficile !',
        'games_50': '🎮 50 parties jouées !',
        'perfect_game': '✨ Partie parfaite (aucune erreur) !'
    }

    for achievement in achievements:
        if achievement in achievement_messages:
            print(f"\n{BRIGHT_YELLOW}🏆 SUCCÈS DÉBLOQUÉ: {achievement_messages[achievement]}{RESET}")
            time.sleep(1)


def play_hangman(player_name):
    """Main function of the game"""
    start_time = time.time()

    clear_screen()
    print(f"Bonjour {player_name} ! 🎮\n")
    difficulty = input("Choisis une difficulté (f-easy/m-middle/d-hard) : ").strip().lower()
    if difficulty == "easy" or difficulty == "f":
        max_errors = 10
        difficulty = 0
    elif difficulty == "middle" or difficulty == "m":
        max_errors = 6
        difficulty = 1
    elif difficulty == "hard" or difficulty == "d":
        max_errors = 3
        difficulty = 2
    else:
        print("Difficulté invalide. Par défaut : middle.")
        difficulty = 1
        max_errors = 6

    secret_word = choose_random_word(difficulty)
    secret_word_normalized = normalize_word(secret_word.lower())
    found_letters = set()
    wrong_letters = set()
    errors = 0
    hints_used = 0

    print(f"Mot à deviner : {len(secret_word)} lettres")
    print(f"{CYAN}💡 Tapez 'indice' pour révéler une lettre (coûte 1 vie){RESET}")

    while errors < max_errors:
        clear_screen()
        print(" ")
        # Visual progress indicator
        if errors > 0:
            print(f"{RED}{draw_progress_bar(errors, max_errors, difficulty)}{RESET}")

        print(f"Mot : {display_masked_word(secret_word, found_letters)}")

        if wrong_letters and difficulty == 0:
            wrong_letters_display = []
            for letter in sorted(wrong_letters):
                wrong_letters_display.append(f"{BRIGHT_RED}{letter}{RESET}")
            print(f"Lettres fausses : {', '.join(wrong_letters_display)}")

        if hints_used > 0:
            print(f"{CYAN}💡  Indices utilisés : {hints_used}{RESET}")

        if word_is_complete(secret_word, found_letters):
            end_time = time.time()
            game_time = end_time - start_time

            # Victory animation
            show_loading_animation("Victoire", 1)
            clear_screen()

            print(f"\n{BRIGHT_GREEN}🎉  BRAVO ! Tu as trouvé le mot : {secret_word}{RESET}")
            print(f"⏱️  Temps de jeu: {game_time:.1f} secondes")
            print(f"❌  Lettres fausses: {len(wrong_letters)}")

            if hints_used > 0:
                print(f"💡  Indices utilisés: {hints_used}")

            # Update stats
            player_stats = update_player_stats(player_name, True, len(secret_word), len(wrong_letters), game_time, difficulty, hints_used, secret_word)

            # Check for achievements
            difficulty_names = ["easy", "middle", "hard"]
            new_achievements = check_achievements(player_stats, difficulty_names)
            if new_achievements:
                display_achievements(new_achievements)

            print(f"\n📊  Tes stats: {player_stats['games_won']} victoires sur {player_stats['games_played']} parties")
            if "current_streak" in player_stats and player_stats['current_streak'] > 1:
                print(f"🔥  Série actuelle: {player_stats['current_streak']}")

            input("\nAppuie sur Entrée pour continuer...")
            return True

        # Get input with the timer for hard mode
        if difficulty == 1 or difficulty == 2:
            game_state = {
                "word_display": display_masked_word(secret_word, found_letters),
                "wrong_letters": wrong_letters,
                "difficulty": difficulty,
                "lives": max_errors - errors
            }

            delay = {1: 10, 2: 5}.get(difficulty, None)

            entry = get_input_with_timer("Entre une lettre ou le mot entier : ", delay, game_state)

            if entry is None:  # Timer expired
                errors += 1
                input("Appuie sur Entrée pour continuer...")
                continue
        else:
            entry = input("\nEntre une lettre ou le mot entier : ").strip().lower()

        if not entry:
            print("Tu dois taper quelque chose !")
            input("Appuie sur Entrée pour continuer...")
            continue

        # Handle hint request
        if entry == "indice":
            if errors >= max_errors - 1:
                print(f"{RED}❌ Tu n'as pas assez de vies pour un indice !{RESET}")
                input("Appuie sur Entrée pour continuer...")
                continue

            hint_letter, original_letter = get_hint(secret_word, found_letters)
            if hint_letter:
                found_letters.add(hint_letter)
                errors += 1
                hints_used += 1
                show_loading_animation("Recherche d'indice", 1)
                print(f"\n{BRIGHT_YELLOW}💡 INDICE: La lettre '{original_letter}' est dans le mot !{RESET}")
                input("Appuie sur Entrée pour continuer...")
                continue
            else:
                print(f"{YELLOW}💡 Aucune lettre cachée disponible pour l'indice !{RESET}")
                input("Appuie sur Entrée pour continuer...")
                continue

        if len(entry) == 1:
            if not is_valid_letter(entry):
                print("Merci d\'entrer une lettre valide !")
                continue

            normalized_letter = normalize_character(entry)

            if normalized_letter in found_letters or normalized_letter in wrong_letters:
                print("Tu as déjà essayé cette lettre !")
                continue

            if normalized_letter in secret_word_normalized:
                found_letters.add(normalized_letter)
                print(f"{BRIGHT_GREEN}✓ Bonne lettre : {entry}{RESET}")
            else:
                wrong_letters.add(normalized_letter)
                errors += 1
                show_loading_animation("Ajout d'une partie du pendu", 0.5)
                print(f"{BRIGHT_RED}✗ Mauvaise lettre : {entry}{RESET}")

        else:
            # Tentative de mot entier
            guess_normalized = normalize_word(entry)
            if guess_normalized == secret_word_normalized:
                # Victoire immédiate
                end_time = time.time()
                game_time = end_time - start_time

                show_loading_animation("Victoire parfaite", 1)
                clear_screen()

                print(f"\n{BRIGHT_GREEN}🎉  BRAVO ! Tu as trouvé le mot entier : {secret_word}{RESET}")
                print(f"⏱️  Temps de jeu: {game_time:.1f} secondes")
                print(f"❌  Lettres fausses: {len(wrong_letters)}")

                if hints_used > 0:
                    print(f"💡  Indices utilisés: {hints_used}")

                # Update stats
                player_stats = update_player_stats(player_name, True, len(secret_word), len(wrong_letters), game_time, difficulty, hints_used, secret_word)

                # Check for achievements
                difficulty_names = ["easy", "middle", "hard"]
                new_achievements = check_achievements(player_stats, difficulty_names)
                if new_achievements:
                    display_achievements(new_achievements)

                print(f"\n📊  Tes stats: {player_stats['games_won']} victoires sur {player_stats['games_played']} parties")
                if "current_streak" in player_stats and player_stats['current_streak'] > 1:
                    print(f"🔥  Série actuelle: {player_stats['current_streak']}")

                input("\nAppuie sur Entrée pour continuer...")
                return True
            else:
                show_loading_animation("Vérification du mot", 0.5)
                print(f"{BRIGHT_RED}✗ Mauvaise proposition de mot : \"{entry}\"{RESET}")
                errors += 1

    # Game over
    show_loading_animation("Défaite", 1)
    clear_screen()

    print(f"{RED}{draw_progress_bar(errors, max_errors, difficulty)}{RESET}")
    end_time = time.time()
    game_time = end_time - start_time

    print(f"\n{BRIGHT_RED}💀  PERDU ! Le mot était : {secret_word}{RESET}")
    print(f"⏱️  Temps de jeu: {game_time:.1f} secondes")
    print(f"❌  Lettres fausses: {len(wrong_letters)}")

    if hints_used > 0:
        print(f"💡  Indices utilisés: {hints_used}")

    # Update stats
    player_stats = update_player_stats(player_name, False, len(secret_word), len(wrong_letters), game_time, difficulty, hints_used, secret_word)

    print(f"\n📊  Tes stats: {player_stats['games_won']} victoires sur {player_stats['games_played']} parties")
    print(f"{RED}💔  Série interrompue{RESET}")

    input("\nAppuie sur Entrée pour continuer...")
    return False


def main():
    """Main function"""
    player_name = None

    while True:
        choice = show_menu()

        if choice == "quit":
            clear_screen()
            print(f"{GREEN}Merci d\'avoir joué ! 👋{RESET}")
            break

        elif choice == "play":
            if not player_name:
                clear_screen()
                player_name = input("Quel est ton nom ? : ").strip()
                if not player_name:
                    player_name = "Joueur"

            play_hangman(player_name)

        elif choice == "stats":
            if not player_name:
                clear_screen()
                player_name = input("Quel est ton nom pour voir tes stats ? : ").strip()
                if not player_name:
                    continue

            show_player_stats(player_name)

        elif choice == "leaderboard":
            show_leaderboard()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print(f"\n{GREEN}Au revoir ! 👋{RESET}")
    except Exception as e:
        clear_screen()
        print(f"{RED}Une erreur est survenue: {e}{RESET}")
        print(f"{YELLOW}Le jeu va se fermer...{RESET}")
        time.sleep(2)