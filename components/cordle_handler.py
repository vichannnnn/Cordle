import datetime
import random
from dataclasses import dataclass
import asyncpg
import hikari
import lightbulb
import pytz
import typing
from lightbulb.ext import tasks
from PGDatabase import Database, pool
from words_dictionary import black_alphabets, green_alphabets, yellow_alphabets
from collections import Counter

plugin = lightbulb.Plugin("Cordle")


async def get_today_word():
    database_object = Database(pool)
    return [i for i in await database_object.fetchrow(' SELECT * FROM five_word_history ORDER BY day_id DESC LIMIT 1 ')]


async def check_word_validity(input: str):
    database_object = Database(pool)
    lst = [i[0] for i in
           await database_object.fetch(' SELECT word FROM five_words UNION SELECT word FROM five_word_history ')]
    if input not in lst:
        return False
    return True


async def to_square(colour: int):
    valid = (0, 1, 2)
    if colour not in valid:
        raise ValueError(f"Colour must be one of {valid}.")
    if colour == 0:
        return ":white_large_square:"
    elif colour == 1:
        return ":green_square:"
    else:
        return ":yellow_square:"


async def to_emote(letter: str, colour: int):
    valid = (0, 1, 2)
    if colour not in valid:
        raise ValueError(f"Colour must be one of {valid}.")
    if colour == 0:
        clr = 'black'
        emoji_id = black_alphabets[letter]
    elif colour == 1:
        clr = 'green'
        emoji_id = green_alphabets[letter]
    else:
        clr = 'yellow'
        emoji_id = yellow_alphabets[letter]
    emoji_text = f"<:{clr}_{letter}:{emoji_id}>"
    return emoji_text


async def new_daily():
    today = datetime.datetime.now(pytz.timezone('Singapore')).date()
    database_object = Database(pool)
    last_record = await database_object.fetchrow('SELECT date FROM daily_tracker WHERE date = $1 ', today)

    if not last_record:  # If today hasn't been recorded yet
        i = 1
        while True:
            try:
                await database_object.execute('INSERT INTO daily_tracker (id,date) VALUES ($1, $2) ', i, today)
                break
            except asyncpg.UniqueViolationError:
                i += 1
                continue

        # Add the word and remove it from the available list
        word_list = [i[0] for i in await database_object.fetch(' SELECT word FROM five_words ')]
        chosen_word = random.choice(word_list)
        await database_object.execute('INSERT INTO five_word_history (day_id, word) VALUES ($1, $2) ', i, chosen_word)
        await database_object.execute('DELETE FROM five_words WHERE word = $1 ', chosen_word)


@tasks.task(s=5)
async def daily_tracker():
    await new_daily()


@plugin.listener(hikari.StartedEvent)
async def on_ready(event: hikari.StartedEvent) -> None:
    daily_tracker.start()


@dataclass
class User:
    user_id: int
    five_words: int = None

    async def get_user_data(self) -> None:
        database_object = Database(pool)
        check = await database_object.fetchrow('SELECT COUNT(*) FROM user_profile WHERE user_id = $1 ', self.user_id)

        if not check[0]:
            await database_object.execute('INSERT INTO user_profile (user_id) VALUES ($1) ', self.user_id)
            self.five_words = 0
            return

        five_words = await database_object.fetchrow('SELECT five_word_solved FROM user_profile WHERE user_id = $1 ',
                                                    self.user_id)
        self.five_words = five_words[0]

    async def play_attempt(self, word: str) -> bool:
        day_id, today_word = await get_today_word()
        answer = [i for i in today_word]
        guess = [i for i in word]
        result = []
        answer_dict = Counter(answer)

        # 0 = Wrong place, wrong letter
        # 1 = Right place, right letter
        # 2 = Wrong place, right letter

        # Cordle Logic
        for n, letter in enumerate(answer):  # Iterate through the first time to snuff out all the right letters and positions.
            if guess[n] == letter:  # If they are in the right position and same letter
                result.append(1)
                answer_dict[letter] -= 1  # Reduce letter counter by one to track duplicate letter
                continue

            if guess[n] in answer_dict:  # If the letter exists, place a temporary mark on the position
                result.append('TBD')

            else:  # If the letter does not even exist at all, mark as black
                result.append(0)

        for n, letter in enumerate(answer):  # Iterate the second time to find the right letter but wrong position letters
            if result[n] == 'TBD':
                if answer_dict[guess[n]] > 0:  # If there are duplicated same letter that still exists, mark as yellow
                    answer_dict[letter] -= 1  # Reduce the counter correspondingly for even more duplicates
                    result[n] = 2
                else:
                    result[n] = 0  # If there are no more duplicate same letter, then it is black now

        attempt = await self.check_today_attempt()
        attempt += 1
        a, e, i, o, u = result
        database_object = Database(pool)
        victory_check = list(set(result))
        await database_object.execute(
            'INSERT INTO daily_five_profile (day_id, user_id, attempt, completed, result1, result2, result3, result4, result5, word_guessed) '
            'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)', day_id, self.user_id, attempt,
            1 if victory_check == [1] else 0, a, e, i, o, u, word)
        if victory_check == [1]:
            self.five_words += 1
            await database_object.execute('UPDATE user_profile SET five_word_solved = $1 WHERE user_id = $2 ',
                                          self.five_words, self.user_id)
        if victory_check == [1]:
            return "WIN"
        elif attempt == 6:
            return "LOSE"
        else:
            return "CONTINUE"

    async def get_progress(self) -> typing.Union[int, bool] or typing.Union[int, []]:
        database_object = Database(pool)
        day_id, today_word = await get_today_word()
        results = await database_object.fetch('SELECT result1, result2, result3, result4, result5, word_guessed '
                                              'FROM daily_five_profile '
                                              'WHERE user_id = $1 AND '
                                              'day_id = $2 AND attempt <= $3 ORDER BY attempt ',
                                              self.user_id, day_id, 6)

        if results:
            return day_id, [dict(i) for i in results]
        else:
            return day_id, None

    async def check_today_attempt(self) -> typing.Union[int, bool]:
        database_object = Database(pool)
        day_id, today_word = await get_today_word()
        attempt = await database_object.fetchrow('SELECT attempt '
                                                 'FROM daily_five_profile '
                                                 'WHERE user_id = $1 AND '
                                                 'day_id = $2 AND attempt <= $3 ORDER BY attempt DESC',
                                                 self.user_id, day_id, 6)
        complete = await database_object.fetchrow('SELECT attempt '
                                                  'FROM daily_five_profile '
                                                  'WHERE user_id = $1 AND '
                                                  'day_id = $2 AND completed = $3',
                                                  self.user_id, day_id, 1)

        if complete:  # If completed for the day, return DONE for attempt
            return "DONE"
        if attempt:
            if attempt[0] == 6:  # If exhausted, return DONE for attempt
                return "DONE"
            return attempt[0]  # Return attempt count
        return 0  # If not attempted at all, return 0 as attempt count


def load(bot):
    bot.add_plugin(plugin)


def unload(bot):
    bot.remove_plugin(plugin)
