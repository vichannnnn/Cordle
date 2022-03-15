import hikari
import lightbulb
from components.cordle_handler import User, to_emote, check_word_validity, to_square, get_today_word
import datetime

plugin = lightbulb.Plugin("Cordle Commands")


def time_to_reset():
    now = datetime.datetime.now()
    next_midnight = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(
        days=1)
    seconds_left = next_midnight.timestamp() - now.timestamp()

    return seconds_left


def dmyConverter(seconds):
    seconds_in_days = 60 * 60 * 24
    seconds_in_hours = 60 * 60
    seconds_in_minutes = 60

    days = seconds // seconds_in_days
    hours = (seconds - (days * seconds_in_days)) // seconds_in_hours
    minutes = ((seconds - (days * seconds_in_days)) - (hours * seconds_in_hours)) // seconds_in_minutes
    seconds_left = seconds - (days * seconds_in_days) - (hours * seconds_in_hours) - (minutes * seconds_in_minutes)

    time_statement = ""

    if days != 0:
        time_statement += f"{round(days)} days, "
    if hours != 0:
        time_statement += f"{round(hours)} hours, "
    if minutes != 0:
        time_statement += f"{round(minutes)} minutes, "
    if seconds_left != 0:
        time_statement += f"{round(seconds_left)} seconds"
    if time_statement[-2:] == ", ":
        time_statement = time_statement[:-1]
    return time_statement


async def get_shareable_result(day_id: int, current_result: []):
    result_lst = []
    progress_text = f'Cordle {day_id} '
    if current_result:
        for result in current_result:
            row = ''
            try:
                result.pop('word_guessed')
            except KeyError:
                pass
            for idx, score in enumerate(result.values()):
                emote = await to_square(score)
                row += f'{emote}'
            result_lst.append(row)
        next = '\n'
        progress_text += f"{len(current_result)}/6"
        progress_text += '\n'
        progress_text += f'{next.join([r for r in result_lst])}'
        return progress_text

    progress_text += f'0/6'
    progress_text += '\n'
    progress_text += 'You have not attempted Cordle today.'
    return progress_text


async def get_result(day_id: int, current_result: []):
    result_lst = []
    progress_text = f'Cordle {day_id} '
    if current_result:
        for result in current_result:
            row = ''
            guessed_word = result['word_guessed']
            result.pop('word_guessed')
            for idx, score in enumerate(result.values()):
                emote = await to_emote(guessed_word[idx], score)
                row += f'{emote}'
            result_lst.append(row)
        next = '\n'
        progress_text += f"{len(current_result)}/6"
        progress_text += '\n'
        progress_text += f'{next.join([r for r in result_lst])}'
        return progress_text

    progress_text += f'0/6'
    progress_text += '\n'
    progress_text += 'You have not attempted Cordle today.'
    return progress_text

@plugin.command()
@lightbulb.command("progress", "Checks your Cordle progress today, if any.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def progress_command(ctx: lightbulb.Context) -> None:
    user_object = User(ctx.author.id)

    day_id, current_result = await user_object.get_progress()
    progress_text = await get_result(day_id, current_result)
    progress_text += '\n\n'
    progress_text += f'New Cordle will be available in {dmyConverter(time_to_reset())}.'
    return await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.command("share", "Gives a shareable Cordle progress result today.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def share_command(ctx: lightbulb.Context) -> None:
    user_object = User(ctx.author.id)
    day_id, current_result = await user_object.get_progress()
    progress_text = await get_shareable_result(day_id, current_result)
    return await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)


@plugin.command()
@lightbulb.option("word", "The word you're submitting.", str)
@lightbulb.command("play", "Starts playing Cordle.")
@lightbulb.implements(lightbulb.PrefixCommand, lightbulb.SlashCommand)
async def play_command(ctx: lightbulb.Context) -> None:
    user_object = User(ctx.author.id)
    await user_object.get_user_data()

    attempt = await user_object.check_today_attempt()

    if attempt == "DONE":  # If out of attempt or completed for today
        await ctx.respond("You have already completed your Cordle for today. Please try again tomorrow!",
                          flags=hikari.MessageFlag.EPHEMERAL)
        day_id, current_result = await user_object.get_progress()
        progress_text = await get_result(day_id, current_result)
        progress_text += '\n\n'
        progress_text += f'New Cordle will be available in {dmyConverter(time_to_reset())}.'
        return await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)

    if len(ctx.options.word) != 5:  # If entered a word that isn't 5 letters.
        day_id, current_result = await user_object.get_progress()
        progress_text = await get_result(day_id, current_result)
        progress_text += '\n\n'
        progress_text += f'New Cordle will be available in {dmyConverter(time_to_reset())}.'
        await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)
        return await ctx.respond("Please make sure you're entering a 5-lettered word. Please try again.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    valid = await check_word_validity(ctx.options.word)

    if not valid:  # If entered a word that does not exist.
        day_id, current_result = await user_object.get_progress()
        progress_text = await get_result(day_id, current_result)
        await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)
        return await ctx.respond("You've entered an invalid word. Please try again.",
                                 flags=hikari.MessageFlag.EPHEMERAL)

    # Finally, allow play attempt
    outcome = await user_object.play_attempt(ctx.options.word)
    day_id, current_result = await user_object.get_progress()
    progress_text = await get_result(day_id, current_result)
    progress_text += '\n\n'
    progress_text += f'New Cordle will be available in {dmyConverter(time_to_reset())}.'
    await ctx.respond(progress_text, flags=hikari.MessageFlag.EPHEMERAL)
    if outcome == "WIN":
        result_text = "Congratulations! You've completed today's Cordle. You can share your result with your friends anytime " \
                      "by copy-pasting the result below or using the `progress` command.\n\n"
        result_text += f"{await get_shareable_result(day_id, current_result)}"
        await ctx.respond(result_text, flags=hikari.MessageFlag.EPHEMERAL)

    elif outcome == "LOSE":
        today_id, today_word = await get_today_word()
        result_text = f"Oh no! The correct word for today is **{today_word}**. Please try again tomorrow!\n\n"
        result_text += f"{await get_shareable_result(day_id, current_result)}"
        await ctx.respond(result_text, flags=hikari.MessageFlag.EPHEMERAL)


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
