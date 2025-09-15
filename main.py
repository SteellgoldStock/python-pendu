import string
import unicodedata
import threading
import time
from list import choose_random_word

RED = "\033[31m"
GREEN = "\033[32m"
RESET = "\033[0m"

def clear_screen():
    print('\033[2J\033[H', end='')

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
                print(f"Lettres fausses : {', '.join(sorted(game_state['wrong_letters']))}")

            lives_display = f"Vies restantes : {(RED + '♥ ' + RESET) * game_state['lives']}"
            if remaining <= 5:  # Red = <= 5 seconds
                lives_display += f" ({RED}⏰ {remaining}s{RESET})"
            else:
                lives_display += f" ({GREEN}⏰ {remaining}s{RESET})"
            print(lives_display)
            print(f"\n{prompt}", end='', flush=True)

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
            print(f"Lettres fausses : {', '.join(sorted(game_state['wrong_letters']))}")
        print(f"Vies restantes : {(RED + '♥ ' + RESET) * game_state['lives']}")
        print(f"\n⏰ Temps écoulé ! Tu perds une vie.")

    return None

def normalize_character(character):
    return unicodedata.normalize('NFD', character).encode('ascii', 'ignore').decode('ascii')

def normalize_word(word):
    return ''.join(normalize_character(c) for c in word)

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


def play_hangman():
    """Main function of the game"""
    difficulty = input("Choisis une difficulté (f-facile/m-moyen/d-difficile) : ").strip().lower()
    if difficulty == "facile" or difficulty == "f":
        max_errors = 10
        difficulty = 0
    elif difficulty == "moyen" or difficulty == "m":
        max_errors = 6
        difficulty = 1
    elif difficulty == "difficile" or difficulty == "d":
        max_errors = 3
        difficulty = 2
    else:
        print("Difficulté invalide. Par défaut : moyen.")
        difficulty = 0
        max_errors = 6

    secret_word = choose_random_word(difficulty)
    secret_word_normalized = normalize_word(secret_word.lower())
    found_letters = set()
    wrong_letters = set()
    errors = 0

    print(f"Mot à deviner : {len(secret_word)} lettres")

    while errors < max_errors:
        clear_screen()
        print(" ")
        # print(draw_hangman(errors))
        print(f"Mot : {display_masked_word(secret_word, found_letters)}")

        if wrong_letters and difficulty == 0:
            print(f"Lettres fausses : {', '.join(sorted(wrong_letters))}")

        print(f"Vies restantes : {(RED + '♥ ' + RESET) * (max_errors - errors)}")

        if word_is_complete(secret_word, found_letters):
            print(f"\n🎉 BRAVO ! Tu as trouvé le mot : {secret_word}")
            return True

        # Get input with the timer for hard mode
        if difficulty == 1 or difficulty == 2:
            game_state = {
                'word_display': display_masked_word(secret_word, found_letters),
                'wrong_letters': wrong_letters,
                'difficulty': difficulty,
                'lives': max_errors - errors
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

        if len(entry) == 1:
            if not is_valid_letter(entry):
                print("Merci d’entrer une lettre valide !")
                continue

            normalized_letter = normalize_character(entry)

            if normalized_letter in found_letters or normalized_letter in wrong_letters:
                print("Tu as déjà essayé cette lettre !")
                continue

            if normalized_letter in secret_word_normalized:
                found_letters.add(normalized_letter)
                print(f"✓ Bonne lettre : {entry}")
            else:
                wrong_letters.add(normalized_letter)
                errors += 1
                print(f"✗ Mauvaise lettre : {entry}")

        else:
            entry = entry[0]

            if not is_valid_letter(entry):
                print("Merci d’entrer une lettre valide !")
                continue

            normalized_letter = normalize_character(entry)

            if normalized_letter in found_letters or normalized_letter in wrong_letters:
                print("Tu as déjà essayé cette lettre !")
                continue

            if normalized_letter in secret_word_normalized:
                found_letters.add(normalized_letter)
                print(f"✓ Bonne lettre : \"{entry}\"")
            else:
                wrong_letters.add(normalized_letter)
                errors += 1
                print(f"✗ Mauvaise lettre : \"{entry}\"")

    # print(draw_hangman(errors))
    print(f"\n💀 PERDU ! Le mot était : {secret_word}")
    return False


def main():
    """Main function"""
    while True:
        ask_name = input("Quel est ton nom ? : ")
        play_hangman()

        replay = input("\nVeux-tu rejouer ? (o/n) : ").strip().lower()
        if replay not in ['o', 'oui', 'y', 'yes']:
            print("Merci d’avoir joué !")
            break


if __name__ == "__main__":
    main()
