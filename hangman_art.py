def draw_progress_bar(errors, max_errors, difficulty):
    """
    Draw a visual progress bar that adapts to the difficulty level
    """
    if difficulty == 0:  # Easy - Health bar style
        remaining_health = max_errors - errors
        health_symbols = "♥" * remaining_health
        lost_symbols = "♡" * errors

        return f"""
    SANTÉ MENTALE
    ╔═══════════════════════╗
    ║ {health_symbols}{lost_symbols} ║
    ╚═══════════════════════╝
    {remaining_health}/{max_errors} tentatives restantes
        """

    elif difficulty == 1:  # Medium - Crystal breaking
        total_bars = 20
        filled_bars = int((max_errors - errors) / max_errors * total_bars)
        empty_bars = total_bars - filled_bars

        if errors == 0:
            crystal_state = "✨ CRISTAL PARFAIT ✨"
        elif errors <= max_errors // 3:
            crystal_state = "💎 Cristal solide"
        elif errors <= 2 * max_errors // 3:
            crystal_state = "💔 Cristal fissuré"
        else:
            crystal_state = "⚠️  Cristal fragile"

        progress = "█" * filled_bars + "░" * empty_bars

        return f"""
    {crystal_state}
    ╔══════════════════════╗
    ║{progress}║
    ╚══════════════════════╝
    {max_errors - errors}/{max_errors} points de vie
        """

    else:  # Hard - Countdown style
        remaining = max_errors - errors

        if remaining == 3:
            status = "🟢 SÉCURISÉ"
        elif remaining == 2:
            status = "🟡 ATTENTION"
        else:
            status = "🔴 DANGER CRITIQUE"

        countdown_display = ""
        for i in range(max_errors):
            if i < errors:
                countdown_display += "💥 "
            else:
                countdown_display += "⭐ "

        return f"""
    {status}
    ╔═════════════════╗
    ║   COMPTE À      ║
    ║     REBOURS     ║
    ║                 ║
    ║  {countdown_display}  ║
    ╚═════════════════╝
    {remaining} chances restantes
        """

def draw_hangman(errors):
    """Legacy function for compatibility - redirects to progress bar"""
    return draw_progress_bar(errors, 6, 1)