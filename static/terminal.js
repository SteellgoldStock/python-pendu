class TerminalPendu {
    constructor() {
        this.output = document.getElementById('terminal-output');
        this.input = document.getElementById('terminal-input');
        this.currentGame = null;
        this.playerName = null;
        this.playerPassword = null;
        this.isAuthenticated = false;
        this.gameStartTime = null;
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
<span class="success">╔═══════════════════════════════════════╗</span>
<span class="success">║      TERMINAL PENDU - CONNEXION       ║</span>
<span class="success">╚═══════════════════════════════════════╝</span>

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
        console.log('showMenu() called');
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
                        console.log('Enter key pressed in menu');
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
            console.log('executeMenuSelection called but not in menu state:', this.gameState);
            return;
        }

        this.cleanupMenuNavigation();
        const selectedItem = this.menuItems[this.selectedMenuItem];
        console.log('Executing menu selection:', selectedItem.command);
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
        console.log('startGame() called - this should not happen automatically!');
        console.trace('startGame called from:');
        this.clearTerminal();
        this.printOutput(`<span class="success">Bonjour ${this.playerName} ! 🎮</span>\n`);

        // Demander la difficulté
        const difficulty = await this.waitForInput('Choisis une difficulté (f-easy/m-middle/d-hard) : ');

        let maxErrors, difficultyLevel, timerDelay;
        const diffStr = difficulty.toLowerCase();

        if (diffStr === 'easy' || diffStr === 'f') {
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
            this.currentGame.wrong_letters = [];
            this.gameStartTime = Date.now();

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
                    this.currentGame.errors++;
                    this.currentGame.lives--;
                    this.clearTerminal();
                    this.displayGameState();
                    this.printOutput('\n⏰  Temps écoulé ! Tu perds une vie.');
                    await this.waitForInput('Appuie sur Entrée pour continuer...');

                    if (this.currentGame.errors >= this.currentGame.max_errors) {
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

        // Afficher l'art de progression si des erreurs
        if (this.currentGame.errors > 0) {
            this.printOutput(`<span class="error">${this.getProgressBar()}</span>`);
        }

        this.printOutput(`Mot : ${this.currentGame.word_display}`);

        // Afficher lettres fausses seulement en mode easy
        if (this.currentGame.wrong_letters.length > 0 && this.currentGame.difficulty_level === 0) {
            const wrongDisplay = this.currentGame.wrong_letters.map(letter => `<span class="bright-red">${letter}</span>`).join(', ');
            this.printOutput(`Lettres fausses : ${wrongDisplay}`);
        }

        if (this.currentGame.hints_used > 0) {
            this.printOutput(`<span class="cyan">💡  Indices utilisés : ${this.currentGame.hints_used}</span>`);
        }
    }

    getProgressBar() {
        const progress = this.currentGame.errors;
        const max = this.currentGame.max_errors;
        const bars = '█'.repeat(progress) + '░'.repeat(max - progress);
        return `[${bars}] ${progress}/${max}`;
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
        this.printOutput(' ');
        this.printOutput(`Mot : ${this.currentGame.word_display}`);

        if (this.currentGame.wrong_letters.length > 0 && this.currentGame.difficulty_level === 0) {
            this.printOutput('Lettres fausses : ' + this.currentGame.wrong_letters.join(', '));
        }

        const hearts = '♥ '.repeat(this.currentGame.lives);
        const timerColor = this.timeRemaining <= 5 ? 'error' : 'success';
        this.printOutput(`Vies restantes : <span class="error">${hearts}</span>(<span class="${timerColor}">⏰ ${this.timeRemaining}s</span>)`);
        this.printOutput(`\n${prompt}`);
    }

    async handleGameInput(input) {
        if (!this.currentGame || !input) return;

        const entry = input.trim().toLowerCase();

        // Gérer la demande d'indice
        if (entry === 'indice') {
            if (this.currentGame.errors >= this.currentGame.max_errors - 1) {
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
        this.currentGame.lives = result.lives;
        this.currentGame.status = result.status;
        this.currentGame.hints_used = result.hints_used || 0;
        this.currentGame.errors = this.currentGame.max_errors - result.lives;
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
        } else {
            await this.showLoadingAnimation('Défaite', 1);
            this.clearTerminal();
            this.printOutput(`<span class="error">${this.getProgressBar()}</span>`);
            this.printOutput(`\n<span class="bright-red">💀  PERDU ! Le mot était : ${secretWord}</span>`);
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

        await this.waitForInput('\nAppuie sur Entrée pour continuer...');
        this.currentGame = null;
        this.showMenu();
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

        let playerName = this.playerName;
        if (!playerName) {
            playerName = await this.waitForInput('Quel est ton nom pour voir tes stats ? : ');
            if (!playerName.trim()) {
                this.showMenu();
                return;
            }
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
}

// Initialize terminal when page loads
document.addEventListener('DOMContentLoaded', () => {
    new TerminalPendu();
});