class TerminalPendu {
    constructor() {
        this.output = document.getElementById('terminal-output');
        this.input = document.getElementById('terminal-input');
        this.currentGame = null;
        this.playerName = null;
        this.playerPassword = null;
        this.isAuthenticated = false;
        this.gameStartTime = null;
        this.sessionStartTime = null; // Pour le mode infini
        this.maxLivesReached = 0; // Pour tracker le max de vies atteint
        this.timer = null;
        this.timeRemaining = 0;
        this.gameState = 'login'; // 'login', 'menu', 'playing', 'waiting_input'
        this.isWaitingForInput = false;
        this.pendingInputResolver = null;

        this.init();
    }

    init() {
        this.showWelcome();
        this.setupInputHandlers();
        this.input.focus();
    }

    setupInputHandlers() {
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();

                // Si on attend une saisie spéciale
                if (this.isWaitingForInput && this.pendingInputResolver) {
                    const value = this.input.value.trim();

                    // Arrêter le timer s'il existe
                    if (this.timer) {
                        clearInterval(this.timer);
                        this.timer = null;
                    }

                    this.input.value = '';
                    this.isWaitingForInput = false;

                    const resolver = this.pendingInputResolver;
                    this.pendingInputResolver = null;
                    resolver(value);
                } else {
                    this.processCommand();
                }
            }
        });

        // Keep focus on input
        document.addEventListener('click', () => {
            this.input.focus();
        });
    }

    showWelcome() {
        this.clearTerminal();
        this.showLoginScreen();
    }

    showLoginScreen() {
        this.clearTerminal();
        const loginScreen = `
<span class="success">════════════════════════════════════════</span>
<span class="success">    TERMINAL PENDU - CONNEXION</span>
<span class="success">════════════════════════════════════════</span>

<span class="warning">🔒 Authentification requise pour jouer</span>
<span class="info">Les comptes sont protégés contre l'usurpation d'identité</span>

<span class="cyan">Commandes disponibles:</span>
<span class="muted">  login [nom] - Se connecter ou créer un compte</span>
<span class="muted">  quit        - Quitter l'application</span>

<span class="warning">Tapez 'login [votre_nom]' pour commencer</span>
`;
        this.printOutput(loginScreen);
        this.gameState = 'login';
    }

    showMenu() {
        this.clearTerminal();
        this.selectedMenuItem = 0;
        this.menuItems = [
            { text: '🎮  Jouer', command: 'play', class: 'success' },
            { text: '📊  Statistiques', command: 'stats', class: 'info' },
            { text: '🏆  Leaderboard', command: 'leaderboard', class: 'cyan' },
            { text: '🚪  Déconnexion', command: 'logout', class: 'warning' },
            { text: '❌  Quitter', command: 'quit', class: 'error' }
        ];

        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput(`<span class="warning">            JEU DU PENDU           </span>`);
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput('');
        this.printOutput(`<span class="info">Connecté en tant que: <span class="success">${this.playerName}</span></span>`);
        this.printOutput('');

        this.renderMenu();
        this.printOutput('');
        this.printOutput(`<span class="muted">Utilisez ↑↓ et Entrée ou cliquez sur une option</span>`);

        this.gameState = 'menu';
        this.setupMenuKeyNavigation();
    }

    renderMenu() {
        this.menuItems.forEach((item, index) => {
            const isSelected = index === this.selectedMenuItem;
            const prefix = isSelected ? '> ' : '  ';
            const highlightClass = isSelected ? 'bright-white' : item.class;
            const menuHtml = `<span class="${highlightClass}" data-menu-index="${index}" style="cursor: pointer; display: block; padding: 2px 0;">${prefix}${item.text}</span>`;
            this.output.innerHTML += menuHtml + '\n';
        });

        // Add click event listeners to menu items (with small delay to prevent auto-trigger)
        setTimeout(() => {
            this.output.querySelectorAll('[data-menu-index]').forEach(element => {
                element.addEventListener('click', (e) => {
                    e.preventDefault();
                    const index = parseInt(e.target.dataset.menuIndex);
                    this.selectedMenuItem = index;
                    this.executeMenuSelection();
                });
            });
        }, 100);
    }

    setupMenuKeyNavigation() {
        // Small delay to prevent residual Enter key from login
        setTimeout(() => {
            this.menuKeyHandler = (e) => {
                if (this.gameState !== 'menu') return;

                switch(e.key) {
                    case 'ArrowUp':
                        e.preventDefault();
                        this.selectedMenuItem = (this.selectedMenuItem - 1 + this.menuItems.length) % this.menuItems.length;
                        this.refreshMenu();
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        this.selectedMenuItem = (this.selectedMenuItem + 1) % this.menuItems.length;
                        this.refreshMenu();
                        break;
                    case 'Enter':
                        e.preventDefault();
                        this.executeMenuSelection();
                        break;
                }
            };

            document.addEventListener('keydown', this.menuKeyHandler);
        }, 200); // 200ms delay to avoid residual keypress
    }

    refreshMenu() {
        // Clear only the menu part and re-render
        this.clearTerminal();
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput(`<span class="warning">            JEU DU PENDU           </span>`);
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput('');
        this.printOutput(`<span class="info">Connecté en tant que: <span class="success">${this.playerName}</span></span>`);
        this.printOutput('');
        this.renderMenu();
        this.printOutput('');
        this.printOutput(`<span class="muted">Utilisez ↑↓ et Entrée ou cliquez sur une option</span>`);
    }

    executeMenuSelection() {
        if (this.gameState !== 'menu') {
            return;
        }

        this.cleanupMenuNavigation();
        const selectedItem = this.menuItems[this.selectedMenuItem];
        this.input.value = selectedItem.command;
        this.processCommand();
    }

    cleanupMenuNavigation() {
        if (this.menuKeyHandler) {
            document.removeEventListener('keydown', this.menuKeyHandler);
            this.menuKeyHandler = null;
        }
    }

    async processCommand() {
        const command = this.input.value.trim();
        if (!command) return;

        this.input.value = '';
        const cmd = command.toLowerCase();

        try {
            if (this.gameState === 'login') {
                // Mode login - seul 'login' et 'quit' sont disponibles
                if (cmd === 'quit' || cmd === 'exit') {
                    this.clearTerminal();
                    this.printOutput('<span class="success">Au revoir ! 👋</span>');
                    this.input.disabled = true;
                    setTimeout(() => { window.close(); }, 1000);
                    return;
                }

                const parts = command.split(' ');
                if (parts[0] === 'login' && parts.length >= 2) {
                    const playerName = parts.slice(1).join(' ').trim();
                    await this.loginPlayer(playerName);
                } else {
                    this.printOutput('<span class="error">Commande invalide</span>');
                    this.printOutput('<span class="muted">Tapez "login [votre_nom]" pour vous connecter</span>');
                }
                return;
            }

            // Mode authentifié - menu principal
            if (this.gameState === 'menu' || !this.gameState || this.gameState === '') {
                switch (cmd) {
                case 'play':
                    await this.startGame();
                    break;
                case 'stats':
                    await this.showStats();
                    break;
                case 'leaderboard':
                    await this.showLeaderboard();
                    break;
                case 'logout':
                    this.logout();
                    break;
                case 'quit':
                case 'exit':
                    this.clearTerminal();
                    this.printOutput('<span class="success">Merci d\'avoir joué ! 👋</span>');
                    this.input.disabled = true;
                    setTimeout(() => { window.close(); }, 1000);
                    break;
                case 'menu':
                    this.showMenu();
                    break;
                case 'clear':
                    this.clearTerminal();
                    break;
                default:
                    this.printOutput(`<span class="error">Commande inconnue: ${cmd}</span>`);
                    this.printOutput('<span class="muted">Tapez "play", "stats", "leaderboard", "logout" ou "quit"</span>');
                    break;
                }
            } else if (this.gameState === 'playing' && this.currentGame) {
                // En mode jeu
                await this.handleGameInput(command);
            } else {
                // État inconnu
                this.printOutput(`<span class="error">État inconnu. Retour au menu...</span>`);
                this.showMenu();
            }
        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
        }
    }

    async loginPlayer(playerName) {
        if (!playerName || playerName.length < 2) {
            this.printOutput('<span class="error">❌ Nom invalide</span>');
            this.printOutput('<span class="muted">Le nom doit contenir au moins 2 caractères</span>');
            return;
        }

        this.clearTerminal();
        this.printOutput(`Connexion pour: <span class="info">${playerName}</span>\n`);

        const password = await this.waitForPasswordInput('Mot de passe (min 3 caractères): ');

        if (!password || password.length < 3) {
            this.printOutput('<span class="error">❌ Mot de passe trop court</span>');
            await this.waitForInput('Appuyez sur Entrée pour continuer...');
            this.showLoginScreen();
            return;
        }

        try {
            const response = await fetch('/api/player/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    player_name: playerName,
                    password: password
                })
            });

            if (!response.ok) {
                const error = await response.json();
                if (response.status === 401) {
                    this.printOutput('<span class="error">❌ Mot de passe incorrect</span>');
                } else {
                    this.printOutput(`<span class="error">Erreur: ${error.detail}</span>`);
                }
                await this.waitForInput('Appuyez sur Entrée pour continuer...');
                this.showLoginScreen();
                return;
            }

            const result = await response.json();
            this.playerName = playerName;
            this.playerPassword = password;
            this.isAuthenticated = true;

            this.clearTerminal();
            if (result.status === 'registered') {
                this.printOutput('<span class="success">✅ Nouveau compte créé !</span>');
                this.printOutput(`<span class="info">${result.message}</span>`);
                this.printOutput('<span class="muted">Votre compte est maintenant protégé par mot de passe.</span>');
            } else if (result.status === 'migrated') {
                this.printOutput('<span class="success">✅ Compte migré avec succès !</span>');
                this.printOutput(`<span class="info">${result.message}</span>`);
            } else {
                this.printOutput('<span class="success">✅ Connexion réussie !</span>');
                this.printOutput(`<span class="info">${result.message}</span>`);
            }

            await this.waitForInput('\nAppuyez sur Entrée pour accéder au menu...');
            this.showMenu();

        } catch (error) {
            this.printOutput(`<span class="error">Erreur de connexion: ${error.message}</span>`);
            await this.waitForInput('Appuyez sur Entrée pour continuer...');
            this.showLoginScreen();
        }
    }

    logout() {
        this.cleanupMenuNavigation();
        this.playerName = null;
        this.playerPassword = null;
        this.isAuthenticated = false;
        this.currentGame = null;
        this.clearTerminal();
        this.printOutput('<span class="info">Déconnexion réussie</span>');
        setTimeout(() => {
            this.showLoginScreen();
        }, 1000);
    }

    async waitForPasswordInput(prompt) {
        this.printOutput(prompt);
        this.isWaitingForInput = true;
        this.pendingInputResolver = null;
        this.input.type = 'password';

        return new Promise((resolve) => {
            this.pendingInputResolver = (value) => {
                this.input.type = 'text';
                resolve(value);
            };
        });
    }

    async startGame() {
        this.clearTerminal();
        this.printOutput(`<span class="success">Bonjour ${this.playerName} ! 🎮</span>\n`);

        // Demander la difficulté
        const difficulty = await this.waitForInput('Choisis une difficulté (f-easy/m-middle/d-hard/i-infini) : ');

        let maxErrors, difficultyLevel, timerDelay, infiniteMode = false;
        const diffStr = difficulty.toLowerCase();

        if (diffStr === 'infini' || diffStr === 'infinite' || diffStr === 'i') {
            // Mode infini - demander la sous-difficulté
            this.printOutput('\n🔄 <span class="cyan">MODE INFINI ACTIVÉ !</span>');
            this.printOutput('<span class="info">Gagne +1 vie à chaque mot trouvé, continue jusqu\'à épuisement !</span>\n');

            const subDifficulty = await this.waitForInput('Choisis la difficulté de base (f-easy/m-middle/d-hard) : ');
            const subDiffStr = subDifficulty.toLowerCase();

            infiniteMode = true;

            if (subDiffStr === 'easy' || subDiffStr === 'f') {
                maxErrors = 10;
                difficultyLevel = 0;
                timerDelay = null;
            } else if (subDiffStr === 'middle' || subDiffStr === 'm') {
                maxErrors = 6;
                difficultyLevel = 1;
                timerDelay = 10;
            } else if (subDiffStr === 'hard' || subDiffStr === 'd') {
                maxErrors = 3;
                difficultyLevel = 2;
                timerDelay = 5;
            } else {
                // Défaut : facile
                maxErrors = 10;
                difficultyLevel = 0;
                timerDelay = null;
            }
        } else if (diffStr === 'easy' || diffStr === 'f') {
            maxErrors = 10;
            difficultyLevel = 0;
            timerDelay = null; // Pas de timer
        } else if (diffStr === 'middle' || diffStr === 'm') {
            maxErrors = 6;
            difficultyLevel = 1;
            timerDelay = 10; // 10 secondes
        } else if (diffStr === 'hard' || diffStr === 'd') {
            maxErrors = 3;
            difficultyLevel = 2;
            timerDelay = 5; // 5 secondes
        } else {
            this.printOutput('Difficulté invalide. Par défaut : middle.');
            maxErrors = 6;
            difficultyLevel = 1;
            timerDelay = 10;
        }

        try {
            const response = await fetch('/api/game/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: this.playerName,
                    password: this.playerPassword,
                    difficulty: ['easy', 'middle', 'hard'][difficultyLevel]
                })
            });

            if (!response.ok) {
                if (response.status === 401) {
                    this.printOutput('<span class="error">❌ Session expirée, reconnectez-vous</span>');
                    await this.waitForInput('Appuyez sur Entrée pour continuer...');
                    this.logout();
                    return;
                }
                throw new Error('Erreur lors de la création du jeu');
            }

            const gameData = await response.json();
            this.currentGame = gameData;
            this.currentGame.max_errors = maxErrors;
            this.currentGame.difficulty_level = difficultyLevel;
            this.currentGame.timer_delay = timerDelay;
            this.currentGame.errors = 0;
            this.currentGame.hints_used = 0;
            this.currentGame.found_letters = [];
            this.currentGame.infinite_mode = infiniteMode;
            this.currentGame.words_found = 0;
            this.currentGame.total_lives_gained = 0;
            this.currentGame.wrong_letters = [];
            this.gameStartTime = Date.now();

            // Initialiser le temps de session pour le mode infini
            if (infiniteMode) {
                this.sessionStartTime = Date.now();
                this.maxLivesReached = this.currentGame.lives;
            }

            this.printOutput(`Mot à deviner : ${gameData.word_display.replace(/_/g, '').length} lettres`);
            if (timerDelay) {
                this.printOutput('<span class="cyan">💡 Attention : Timer activé !</span>');
            }
            this.printOutput('<span class="cyan">💡 Tapez \'indice\' pour révéler une lettre (coûte 1 vie)</span>');

            this.cleanupMenuNavigation();
            this.gameState = 'playing';
            await this.playGame();

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
            await this.waitForInput('\nAppuie sur Entrée pour continuer...');
            this.showMenu();
        }
    }

    async playGame() {
        while (this.currentGame && this.currentGame.status === 'playing') {
            this.clearTerminal();
            this.displayGameState();

            // Vérifier si le jeu est terminé
            if (this.currentGame.status !== 'playing') {
                break;
            }

            let input;
            if (this.currentGame.timer_delay) {
                input = await this.waitForInputWithTimer('Entre une lettre ou le mot entier : ', this.currentGame.timer_delay);

                if (input === null) {
                    // Timer expiré
                    this.currentGame.lives--;  // Décrémenter les vies directement
                    this.currentGame.errors++;  // Maintenir errors pour la cohérence
                    this.clearTerminal();
                    this.displayGameState();
                    this.printOutput('\n⏰  Temps écoulé ! Tu perds une vie.');
                    await this.waitForInput('Appuie sur Entrée pour continuer...');

                    // Vérifier la défaite avec les vies
                    if (this.currentGame.lives <= 0) {
                        await this.endGame(false);
                        return;
                    }
                    continue;
                }
            } else {
                input = await this.waitForInput('\nEntre une lettre ou le mot entier : ');
            }

            await this.handleGameInput(input);
        }
    }

    displayGameState() {
        this.printOutput(' ');
        if (this.currentGame.difficulty_level === 0) {
            this.printOutput(`Mot : ${this.currentGame.word_display} (` + this.currentGame.word_display.length + ')');
        } else {
            this.printOutput(`Mot : ${this.currentGame.word_display}`);
        }

        // Afficher lettres fausses seulement en mode easy
        if (this.currentGame.wrong_letters.length > 0 && this.currentGame.difficulty_level === 0) {
            const wrongDisplay = this.currentGame.wrong_letters.map(letter => `<span class="bright-red">${letter}</span>`).join(', ');
            this.printOutput(`Lettres fausses : ${wrongDisplay}`);
        }

        // Afficher les vies restantes (comme dans le script Python)
        const hearts = '<span class="error">♥ </span>'.repeat(this.currentGame.lives);
        this.printOutput(`Vies restantes : ${hearts}`);

        if (this.currentGame.hints_used > 0) {
            this.printOutput(`<span class="cyan">💡  Indices utilisés : ${this.currentGame.hints_used}</span>`);
        }
    }

    async waitForInput(prompt, timeout = null) {
        if (prompt) this.printOutput(prompt);

        this.isWaitingForInput = true;
        this.pendingInputResolver = null;

        return new Promise((resolve) => {
            this.pendingInputResolver = resolve;
        });
    }

    async waitForInputWithTimer(prompt, seconds) {
        this.isWaitingForInput = true;
        this.pendingInputResolver = null;

        return new Promise((resolve) => {
            this.timeRemaining = seconds;
            this.pendingInputResolver = resolve;

            this.updateTimerDisplay(prompt);

            this.timer = setInterval(() => {
                this.timeRemaining--;
                this.updateTimerDisplay(prompt);

                if (this.timeRemaining <= 0) {
                    clearInterval(this.timer);
                    this.timer = null;
                    if (this.pendingInputResolver) {
                        const resolver = this.pendingInputResolver;
                        this.pendingInputResolver = null;
                        this.isWaitingForInput = false;
                        resolver(null); // Timer expiré
                    }
                }
            }, 1000);
        });
    }

    updateTimerDisplay(prompt) {
        if (!this.currentGame) return;

        this.clearTerminal();
        this.displayGameState();

        // Ajouter juste le timer à l'affichage des vies existant
        const timerColor = this.timeRemaining <= 5 ? 'error' : 'success';
        this.printOutput(`(<span class="${timerColor}">⏰ ${this.timeRemaining}s</span>)`);
        this.printOutput(`\n${prompt}`);
    }

    async handleGameInput(input) {
        if (!this.currentGame || !input) return;

        const entry = input.trim().toLowerCase();

        // Gérer la demande d'indice
        if (entry === 'indice') {
            if (this.currentGame.lives <= 1) {  // Doit avoir au moins 1 vie après l'indice
                this.printOutput('<span class="error">❌ Tu n\'as pas assez de vies pour un indice !</span>');
                await this.waitForInput('Appuie sur Entrée pour continuer...');
                return;
            }

            try {
                const response = await fetch('/api/game/guess', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        game_id: this.currentGame.game_id,
                        guess: entry,
                        hint_requested: true
                    })
                });

                const result = await response.json();
                this.updateGameState(result);

                this.printOutput(`\n<span class="bright-yellow">${result.message}</span>`);
                await this.waitForInput('Appuie sur Entrée pour continuer...');
                return;
            } catch (error) {
                this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
                return;
            }
        }

        // Traiter la tentative normale
        try {
            const response = await fetch('/api/game/guess', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    game_id: this.currentGame.game_id,
                    guess: entry,
                    hint_requested: false
                })
            });

            const result = await response.json();
            this.updateGameState(result);

            // Afficher le résultat
            if (entry.length === 1) {
                if (result.message.includes('✓')) {
                    this.printOutput(`<span class="bright-green">${result.message}</span>`);
                } else {
                    this.printOutput(`<span class="bright-red">${result.message}</span>`);
                    await this.showLoadingAnimation('Ajout d\'une partie du pendu', 0.5);
                }
            } else {
                if (result.status === 'won') {
                    await this.showLoadingAnimation('Victoire parfaite', 1);
                } else {
                    await this.showLoadingAnimation('Vérification du mot', 0.5);
                    this.printOutput(`<span class="bright-red">${result.message}</span>`);
                }
            }

            // Vérifier fin de partie
            if (result.status === 'won') {
                await this.endGame(true);
            } else if (result.status === 'lost') {
                await this.endGame(false);
            }

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
        }
    }

    updateGameState(result) {
        this.currentGame.word_display = result.word_display;
        this.currentGame.wrong_letters = result.wrong_letters || [];

        // En mode infini, conserver les vies accumulées (ne pas écraser par la réponse serveur)
        if (!this.currentGame.infinite_mode) {
            // Mode normal : utiliser directement les vies du serveur
            this.currentGame.lives = result.lives;
            this.currentGame.errors = this.currentGame.max_errors - result.lives;
        } else {
            // Mode infini : ajuster les vies selon la différence serveur/client
            const serverLives = result.lives;
            const expectedClientLives = this.currentGame.max_errors - (this.currentGame.max_errors - serverLives);

            // Si le serveur indique moins de vies, le joueur en a perdu
            if (serverLives < expectedClientLives) {
                const livesLost = expectedClientLives - serverLives;
                this.currentGame.lives -= livesLost;
            }

            // Synchroniser les erreurs
            this.currentGame.errors = this.currentGame.max_errors - serverLives;
        }

        this.currentGame.status = result.status;
        this.currentGame.hints_used = result.hints_used || 0;
        if (result.secret_word) {
            this.currentGame.secret_word = result.secret_word;
        }
    }

    async endGame(won) {
        const gameTime = (Date.now() - this.gameStartTime) / 1000;
        const secretWord = this.currentGame.secret_word || this.currentGame.word_display || 'ERREUR';

        if (won) {
            await this.showLoadingAnimation('Victoire', 1);
            this.clearTerminal();
            this.printOutput(`\n<span class="bright-green">🎉  BRAVO ! Tu as trouvé le mot : ${secretWord}</span>`);

            // Mode infini : gagner +1 vie
            if (this.currentGame.infinite_mode) {
                this.currentGame.lives++;
                this.currentGame.words_found++;
                this.currentGame.total_lives_gained++;

                // Mettre à jour le max de vies atteint
                this.maxLivesReached = Math.max(this.maxLivesReached, this.currentGame.lives);

                const hearts = '<span class="error">♥ </span>'.repeat(this.currentGame.lives);
                this.printOutput(`<span class="success">🔄 MODE INFINI : +1 vie ! (Vies restantes : ${hearts})</span>`);
                this.printOutput(`<span class="info">📊 Mots trouvés : ${this.currentGame.words_found} | Vies gagnées : ${this.currentGame.total_lives_gained}</span>`);
            }
        } else {
            await this.showLoadingAnimation('Défaite', 1);
            this.clearTerminal();
            this.printOutput(`\n<span class="bright-red">💀  PERDU ! Le mot était : ${secretWord}</span>`);

            if (this.currentGame.infinite_mode) {
                this.printOutput(`<span class="warning">🔄 MODE INFINI TERMINÉ !</span>`);
                this.printOutput(`<span class="info">📊 Performance finale :</span>`);
                this.printOutput(`<span class="info">   • Mots trouvés : ${this.currentGame.words_found}</span>`);
                this.printOutput(`<span class="info">   • Vies gagnées : ${this.currentGame.total_lives_gained}</span>`);

                // Enregistrer les statistiques du mode infini
                await this.saveInfiniteStats();
            }
        }

        this.printOutput(`⏱️  Temps de jeu: ${gameTime.toFixed(1)} secondes`);
        this.printOutput(`❌  Lettres fausses: ${this.currentGame.wrong_letters.length}`);

        if (this.currentGame.hints_used > 0) {
            this.printOutput(`💡  Indices utilisés: ${this.currentGame.hints_used}`);
        }

        // Afficher stats courtes
        try {
            const response = await fetch(`/api/stats/${encodeURIComponent(this.playerName)}`);
            if (response.ok) {
                const stats = await response.json();
                const gamesWon = stats.games_won || 0;
                const gamesPlayed = stats.games_played || 0;
                const currentStreak = stats.current_streak || 0;

                this.printOutput(`\n📊  Tes stats: ${gamesWon} victoires sur ${gamesPlayed} parties`);
                if (won && currentStreak > 1) {
                    this.printOutput(`🔥  Série actuelle: ${currentStreak}`);
                } else if (!won) {
                    this.printOutput('<span class="error">💔  Série interrompue</span>');
                }
            }
        } catch (e) {
            // Ignore stats errors
        }

        // Mode infini : continuer automatiquement si victoire
        if (this.currentGame.infinite_mode && won) {
            await this.waitForInput('\nAppuie sur Entrée pour le mot suivant...');

            // Démarrer un nouveau mot
            await this.startNewWordInfinite();
        } else if (!won) {
            // Menu après défaite
            await this.showDefeatMenu();
        } else {
            await this.waitForInput('\nAppuie sur Entrée pour continuer...');
            this.currentGame = null;
            this.showMenu();
        }
    }

    async showDefeatMenu() {
        this.printOutput('\n');
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput(`<span class="warning">          QUE VEUX-TU FAIRE ?           </span>`);
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>\n`);

        const defeatMenuItems = [
            { text: '🔄  Rejouer (même difficulté)', command: 'replay', class: 'success' },
            { text: '⚙️   Changer de mode', command: 'change', class: 'info' },
            { text: '🏠  Retour à l\'accueil', command: 'home', class: 'warning' }
        ];

        const choice = await this.showSelectionMenu(defeatMenuItems, 'Choisis ton action :');

        switch(choice) {
            case 'replay':
                await this.replayGame();
                break;
            case 'change':
                this.currentGame = null;
                await this.startGame(); // Retour au choix de difficulté
                break;
            case 'home':
            default:
                this.currentGame = null;
                this.showMenu();
                break;
        }
    }

    async replayGame() {
        try {
            // Relancer avec les mêmes paramètres
            const savedDifficultyLevel = this.currentGame.difficulty_level;
            const savedMaxErrors = this.currentGame.max_errors;
            const savedTimerDelay = this.currentGame.timer_delay;
            const savedInfiniteMode = this.currentGame.infinite_mode;

            const response = await fetch('/api/game/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: this.playerName,
                    password: this.playerPassword,
                    difficulty: ['easy', 'middle', 'hard'][savedDifficultyLevel]
                })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la création du nouveau jeu');
            }

            const gameData = await response.json();
            this.currentGame = gameData;

            // Restaurer les paramètres
            this.currentGame.max_errors = savedMaxErrors;
            this.currentGame.difficulty_level = savedDifficultyLevel;
            this.currentGame.timer_delay = savedTimerDelay;
            this.currentGame.errors = 0;
            this.currentGame.hints_used = 0;
            this.currentGame.found_letters = [];
            this.currentGame.wrong_letters = [];

            // Réinitialiser le mode infini si c'était actif
            if (savedInfiniteMode) {
                this.currentGame.infinite_mode = true;
                this.currentGame.words_found = 0;
                this.currentGame.total_lives_gained = 0;
                this.sessionStartTime = Date.now();
                this.maxLivesReached = this.currentGame.lives;
            }

            this.gameStartTime = Date.now();
            this.clearTerminal();

            if (savedInfiniteMode) {
                this.printOutput(`<span class="cyan">🔄 NOUVEAU JEU - MODE INFINI</span>`);
                const hearts = '<span class="error">♥ </span>'.repeat(this.currentGame.lives);
                this.printOutput(`<span class="info">Vies de départ : ${hearts}</span>\n`);
            } else {
                this.printOutput(`<span class="success">🎮 NOUVEAU JEU</span>\n`);
            }

            this.printOutput(`Mot à deviner : ${gameData.word_display.replace(/_/g, '').length} lettres`);

            if (this.currentGame.timer_delay) {
                this.printOutput('<span class="cyan">💡 Attention : Timer activé !</span>');
            }
            this.printOutput('<span class="cyan">💡 Tapez \'indice\' pour révéler une lettre (coûte 1 vie)</span>');

            this.cleanupMenuNavigation();
            this.gameState = 'playing';
            await this.playGame();

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
            await this.waitForInput('\nAppuie sur Entrée pour retourner au menu...');
            this.currentGame = null;
            this.showMenu();
        }
    }

    async startNewWordInfinite() {
        try {
            // Conserver les paramètres actuels (APRÈS avoir gagné +1 vie)
            const savedLives = this.currentGame.lives; // Les vies incluent déjà le +1 de la victoire
            const savedWordsFound = this.currentGame.words_found;
            const savedTotalLivesGained = this.currentGame.total_lives_gained;
            const savedMaxErrors = this.currentGame.max_errors;
            const savedDifficultyLevel = this.currentGame.difficulty_level;
            const savedTimerDelay = this.currentGame.timer_delay;

            // Demander un nouveau mot
            const response = await fetch('/api/game/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: this.playerName,
                    password: this.playerPassword,
                    difficulty: ['easy', 'middle', 'hard'][savedDifficultyLevel]
                })
            });

            if (!response.ok) {
                throw new Error('Erreur lors de la création du nouveau mot');
            }

            const gameData = await response.json();
            this.currentGame = gameData;

            // Restaurer les paramètres sauvés (en conservant les vies correctes)
            this.currentGame.lives = savedLives; // Garde les vies actuelles (avec le +1)
            this.currentGame.words_found = savedWordsFound;
            this.currentGame.total_lives_gained = savedTotalLivesGained;
            this.currentGame.max_errors = savedMaxErrors;
            this.currentGame.difficulty_level = savedDifficultyLevel;
            this.currentGame.timer_delay = savedTimerDelay;
            this.currentGame.errors = 0;
            this.currentGame.hints_used = 0;
            this.currentGame.found_letters = [];
            this.currentGame.infinite_mode = true;
            this.currentGame.wrong_letters = [];

            // Redémarrer le chrono pour ce nouveau mot
            this.gameStartTime = Date.now();

            this.clearTerminal();
            this.printOutput(`<span class="cyan">🔄 NOUVEAU MOT - MODE INFINI</span>`);
            const hearts = '<span class="error">♥ </span>'.repeat(this.currentGame.lives);
            this.printOutput(`<span class="info">📊 Mots trouvés : ${this.currentGame.words_found} | Vies restantes : ${hearts}</span>\n`);

            this.printOutput(`Mot à deviner : ${gameData.word_display.replace(/_/g, '').length} lettres`);

            if (this.currentGame.timer_delay) {
                this.printOutput('<span class="cyan">💡 Attention : Timer activé !</span>');
            }
            this.printOutput('<span class="cyan">💡 Tapez \'indice\' pour révéler une lettre (coûte 1 vie)</span>');

            this.cleanupMenuNavigation();
            this.gameState = 'playing';
            await this.playGame();

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
            await this.waitForInput('\nAppuie sur Entrée pour retourner au menu...');
            this.currentGame = null;
            this.showMenu();
        }
    }

    async showSelectionMenu(menuItems, prompt) {
        return new Promise((resolve) => {
            let selectedIndex = 0;

            const renderSelectionMenu = () => {
                // Clear previous menu items only
                const lines = this.output.innerHTML.split('\n');
                const menuStartIndex = lines.findIndex(line => line.includes(prompt));
                if (menuStartIndex !== -1) {
                    // Keep everything before the prompt
                    this.output.innerHTML = lines.slice(0, menuStartIndex).join('\n') + '\n';
                }

                this.printOutput(`<span class="cyan">${prompt}</span>\n`);

                menuItems.forEach((item, index) => {
                    const isSelected = index === selectedIndex;
                    const prefix = isSelected ? '> ' : '  ';
                    const highlightClass = isSelected ? 'bright-white' : item.class;
                    const menuHtml = `<span class="${highlightClass}" data-selection-index="${index}" style="cursor: pointer; display: block; padding: 2px 0;">${prefix}${item.text}</span>`;
                    this.output.innerHTML += menuHtml + '\n';
                });

                this.printOutput('\n<span class="muted">Utilisez ↑↓ et Entrée ou cliquez sur une option</span>');

                // Add click event listeners
                setTimeout(() => {
                    this.output.querySelectorAll('[data-selection-index]').forEach(element => {
                        element.addEventListener('click', (e) => {
                            e.preventDefault();
                            selectedIndex = parseInt(e.target.dataset.selectionIndex);
                            cleanup();
                            resolve(menuItems[selectedIndex].command);
                        });
                    });
                }, 100);
            };

            const keyHandler = (e) => {
                switch(e.key) {
                    case 'ArrowUp':
                        e.preventDefault();
                        selectedIndex = (selectedIndex - 1 + menuItems.length) % menuItems.length;
                        renderSelectionMenu();
                        break;
                    case 'ArrowDown':
                        e.preventDefault();
                        selectedIndex = (selectedIndex + 1) % menuItems.length;
                        renderSelectionMenu();
                        break;
                    case 'Enter':
                        e.preventDefault();
                        cleanup();
                        resolve(menuItems[selectedIndex].command);
                        break;
                    case 'Escape':
                        e.preventDefault();
                        cleanup();
                        resolve(null);
                        break;
                }
            };

            const cleanup = () => {
                document.removeEventListener('keydown', keyHandler);
                // Remove click listeners
                this.output.querySelectorAll('[data-selection-index]').forEach(element => {
                    element.replaceWith(element.cloneNode(true));
                });
            };

            // Initial render
            renderSelectionMenu();

            // Setup keyboard navigation with delay
            setTimeout(() => {
                document.addEventListener('keydown', keyHandler);
            }, 200);
        });
    }

    async showLoadingAnimation(message, duration) {
        const chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏";
        const iterations = Math.floor(duration * 10);

        for (let i = 0; i < iterations; i++) {
            const char = chars[i % chars.length];
            // Simpler animation - just show message
            await new Promise(resolve => setTimeout(resolve, 100));
        }

        this.printOutput(`${message}...`);
    }

    async showStats() {
        this.clearTerminal();

        // Menu de sélection pour les stats
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>`);
        this.printOutput(`<span class="warning">         STATISTIQUES - SÉLECTION        </span>`);
        this.printOutput(`<span class="warning">═══════════════════════════════════════</span>\n`);

        const statsMenuItems = [
            { text: '👤  Mes statistiques', command: 'me', class: 'success' },
            { text: '🔍  Statistiques d\'un autre joueur', command: 'other', class: 'info' }
        ];

        const choice = await this.showSelectionMenu(statsMenuItems, 'Que veux-tu voir ?');

        let playerName;
        if (choice === 'me') {
            playerName = this.playerName;
        } else if (choice === 'other') {
            playerName = await this.waitForInput('Nom du joueur à consulter : ');
            if (!playerName.trim()) {
                this.showMenu();
                return;
            }
        } else {
            this.showMenu();
            return;
        }

        try {
            const response = await fetch(`/api/stats/${encodeURIComponent(playerName)}`);

            if (!response.ok) {
                if (response.status === 404) {
                    this.printOutput(`<span class="error">Aucune statistique trouvée pour ${playerName}</span>`);
                } else {
                    this.printOutput('<span class="error">Erreur lors de la récupération des stats</span>');
                }
                await this.waitForInput('Appuyez sur Entrée pour continuer...');
                this.showMenu();
                return;
            }

            const stats = await response.json();
            this.clearTerminal();

            this.printOutput(`<span class="info">═══════════════════════════════════════</span>`);
            this.printOutput(`<span class="info">       STATISTIQUES DE ${playerName.toUpperCase()}       </span>`);
            this.printOutput(`<span class="info">═══════════════════════════════════════</span>\n`);

            const gamesPlayed = stats.games_played || 0;
            const gamesWon = stats.games_won || 0;
            const totalWordsFound = stats.total_words_found || 0;
            const totalWrongLetters = stats.total_wrong_letters || 0;
            const totalTime = stats.total_time || 0;

            this.printOutput(`🎮  Parties jouées: ${gamesPlayed}`);
            this.printOutput(`🏆  Parties gagnées: ${gamesWon}`);

            if (gamesPlayed > 0) {
                const winRate = ((gamesWon / gamesPlayed) * 100).toFixed(1);
                this.printOutput(`📈  Taux de réussite: ${winRate}%`);
            }

            this.printOutput(`📝  Mots trouvés: ${totalWordsFound}`);
            this.printOutput(`❌  Lettres fausses totales: ${totalWrongLetters}`);

            if (totalTime > 0 && gamesPlayed > 0) {
                const avgTime = (totalTime / gamesPlayed).toFixed(1);
                this.printOutput(`⏱️  Temps moyen par partie: ${avgTime}s`);
            }

            if (stats.best_time) {
                this.printOutput(`⚡  Meilleur temps: ${stats.best_time.toFixed(1)}s`);
            }

            const longestWord = stats.longest_word || 0;
            this.printOutput(`📏  Mot le plus long trouvé: ${longestWord} lettres`);

            const currentStreak = stats.current_streak || 0;
            const bestStreak = stats.best_streak || 0;
            const totalHints = stats.total_hints || 0;

            this.printOutput(`🔥  Série actuelle: ${currentStreak}`);
            this.printOutput(`🏆  Meilleure série: ${bestStreak}`);
            this.printOutput(`💡  Indices utilisés: ${totalHints}`);

            // Statistiques du mode infini
            const infiniteStats = stats.infinite_mode_stats || {};
            if (infiniteStats.games_played > 0) {
                this.printOutput(`\n<span class="cyan">🔄  Statistiques MODE INFINI:</span>`);
                this.printOutput(`  Sessions jouées: ${infiniteStats.games_played}`);
                this.printOutput(`  Meilleur score: ${infiniteStats.best_words_found} mots trouvés`);
                if (infiniteStats.average_words_found > 0) {
                    this.printOutput(`  Moyenne de mots: ${infiniteStats.average_words_found.toFixed(1)} par session`);
                }
                this.printOutput(`  Max de vies atteint: ${infiniteStats.max_lives_reached}`);
                this.printOutput(`  Total vies gagnées: ${infiniteStats.total_lives_gained}`);
                if (infiniteStats.best_session_time) {
                    this.printOutput(`  Meilleure session: ${infiniteStats.best_session_time.toFixed(1)}s`);
                }
                if (infiniteStats.total_session_time > 0 && infiniteStats.games_played > 0) {
                    const avgSessionTime = (infiniteStats.total_session_time / infiniteStats.games_played).toFixed(1);
                    this.printOutput(`  Temps moyen session: ${avgSessionTime}s`);
                }
            }

            this.printOutput(`\n<span class="warning">Répartition par difficulté:</span>`);
            const difficultyStats = stats.difficulty_stats || {};
            for (const [diff, count] of Object.entries(difficultyStats)) {
                const gameCount = count || 0;
                this.printOutput(`  ${diff.charAt(0).toUpperCase() + diff.slice(1)}: ${gameCount} parties`);
            }

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
        }

        await this.waitForInput(`\n<span class="success">Appuyez sur Entrée pour retourner au menu...</span>`);
        this.showMenu();
    }

    async showLeaderboard() {
        this.clearTerminal();

        try {
            const response = await fetch('/api/leaderboard');
            if (!response.ok) {
                throw new Error('Erreur lors de la récupération du leaderboard');
            }

            const leaderboard = await response.json();

            this.printOutput('<span class="warning">═══════════════════════════════════════</span>');
            this.printOutput('<span class="warning">            LEADERBOARD            </span>');
            this.printOutput('<span class="warning">═══════════════════════════════════════</span>\n');

            if (leaderboard.players_by_wins.length > 0) {
                this.printOutput('<span class="success">🏆  Top Victoires:</span>');
                leaderboard.players_by_wins.forEach((player, index) => {
                    this.printOutput(`${index + 1}. ${player[0]}: ${player[1].games_won} victoires`);
                });
                this.printOutput('');
            }

            if (leaderboard.players_by_winrate.length > 0) {
                this.printOutput('<span class="info">📈  Meilleur taux de réussite (min 3 parties):</span>');
                leaderboard.players_by_winrate.forEach((player, index) => {
                    const rate = ((player[1].games_won / player[1].games_played) * 100).toFixed(1);
                    this.printOutput(`${index + 1}. ${player[0]}: ${rate}% (${player[1].games_won}/${player[1].games_played})`);
                });
                this.printOutput('');
            }

            if (leaderboard.players_by_speed.length > 0) {
                this.printOutput('<span class="cyan">⚡  Plus rapides:</span>');
                leaderboard.players_by_speed.forEach((player, index) => {
                    this.printOutput(`${index + 1}. ${player[0]}: ${player[1].best_time.toFixed(1)}s`);
                });
            }

            if (leaderboard.players_by_wins.length === 0) {
                this.printOutput('<span class="warning">Aucune statistique disponible</span>');
            }

        } catch (error) {
            this.printOutput(`<span class="error">Erreur: ${error.message}</span>`);
        }

        await this.waitForInput(`\n<span class="success">Appuyez sur Entrée pour retourner au menu...</span>`);
        this.showMenu();
    }

    clearTerminal() {
        this.output.innerHTML = '';
    }

    printOutput(text) {
        this.output.innerHTML += text + '\n';
        this.scrollToBottom();
    }

    scrollToBottom() {
        this.output.scrollTop = this.output.scrollHeight;
    }

    async saveInfiniteStats() {
        if (!this.currentGame.infinite_mode || !this.sessionStartTime) return;

        try {
            const sessionTime = (Date.now() - this.sessionStartTime) / 1000;

            const response = await fetch('/api/infinite/stats', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    player_name: this.playerName,
                    password: this.playerPassword,
                    words_found: this.currentGame.words_found || 0,
                    lives_gained: this.currentGame.total_lives_gained || 0,
                    max_lives: this.maxLivesReached || 0,
                    session_time: sessionTime
                })
            });

            if (!response.ok) {
                console.warn('Erreur lors de la sauvegarde des stats du mode infini');
            }
        } catch (error) {
            console.warn('Erreur lors de la sauvegarde des stats du mode infini:', error);
        }
    }
}

// Initialize terminal when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TerminalPendu();
});