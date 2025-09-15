import random
import string
import unicodedata
from list import words

from hangman_art import draw_hangman

def normalize_character(character):
    return unicodedata.normalize('NFD', character).encode('ascii', 'ignore').decode('ascii')

def normalize_word(word):
    return ''.join(normalize_character(c) for c in word)

def choose_random_word():
    return random.choice(list(words))

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
    secret_word = choose_random_word()
    secret_word_normalized = normalize_word(secret_word.lower())
    found_letters = set()
    wrong_letters = set()
    errors = 0
    max_errors = 6

    print("=== HANGMAN GAME ===")
    print(f"Word to guess: {len(secret_word)} letters")

    while errors < max_errors:
        print(draw_hangman(errors))
        print(f"Word: {display_masked_word(secret_word, found_letters)}")

        if wrong_letters:
            print(f"Wrong letters: {', '.join(sorted(wrong_letters))}")

        print(f"Lives left: {max_errors - errors}")

        if word_is_complete(secret_word, found_letters):
            print(f"\n🎉 CONGRATULATIONS! You found the word: {secret_word}")
            return True

        entry = input("\nEnter a letter or the whole word: ").strip().lower()

        if not entry:
            print("Please type something!")
            continue

        if len(entry) == 1:
            if not is_valid_letter(entry):
                print("Please enter a valid letter!")
                continue

            normalized_letter = normalize_character(entry)

            if normalized_letter in found_letters or normalized_letter in wrong_letters:
                print("You already tried this letter!")
                continue

            if normalized_letter in secret_word_normalized:
                found_letters.add(normalized_letter)
                print(f"✓ Good letter: {entry}")
            else:
                wrong_letters.add(normalized_letter)
                errors += 1
                print(f"✗ Wrong letter: {entry}")

        else:
            if normalize_word(entry) == secret_word_normalized:
                print(f"\n🎉 CONGRATULATIONS! You found the word: {secret_word}")
                return True
            else:
                errors += 1
                print(f"✗ That's not the right word!")

    print(draw_hangman(errors))
    print(f"\n💀 GAME OVER! The word was: {secret_word}")
    return False


def main():
    """Main function"""
    while True:
        result = play_hangman()

        replay = input("\nDo you want to play again? (y/n): ").strip().lower()
        if replay not in ['o', 'oui', 'y', 'yes']:
            print("Thanks for playing!")
            break


if __name__ == "__main__":
    main()
