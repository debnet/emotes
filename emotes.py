import peewee
import random
import os
from collections import namedtuple
from flask import Flask, render_template, redirect, request


DATABASE = 'emotes.db'
SCORE_0, SCORE_1, SCORE_2, SCORE_3 = 0, 1, 2, 3
app = application = Flask(__name__)
db = peewee.SqliteDatabase(DATABASE)
Message = namedtuple('Message', ('message', 'level'))
Stats = namedtuple('Stats', ('name', 'total', 'score', 'rate_0', 'rate_1', 'rate_2', 'rate_3'))


class Emote(peewee.Model):
    name = peewee.CharField(unique=True)
    vote_0 = peewee.IntegerField(default=0)
    vote_1 = peewee.IntegerField(default=0)
    vote_2 = peewee.IntegerField(default=0)
    vote_3 = peewee.IntegerField(default=0)

    @property
    def ident(self):
        name, ext = os.path.splitext(self.name)
        return name.lower().replace('_', '-').replace(' ', '-').replace('.', '-')

    @property
    def stats(self):
        return Stats(
            name=self.name, total=self.total, score=self.score,
            rate_0=round((self.vote_0 / (self.total or 1)) * 100, 2),
            rate_1=round((self.vote_1 / (self.total or 1)) * 100, 2),
            rate_2=round((self.vote_2 / (self.total or 1)) * 100, 2),
            rate_3=round((self.vote_3 / (self.total or 1)) * 100, 2))

    @property
    def total(self):
        return self.vote_0 + self.vote_1 + self.vote_2 + self.vote_3

    @property
    def score(self):
        return self.vote_0 * SCORE_0 + self.vote_1 * SCORE_1 + self.vote_2 * SCORE_2 + self.vote_3 * SCORE_3

    def set(self, value):
        if value == '0':
            self.vote_0 += 1
        elif value == '1':
            self.vote_1 += 1
        elif value == '2':
            self.vote_2 += 1
        elif value == '3':
            self.vote_3 += 1

    class Meta:
        database = db


db.create_tables([Emote])
prev_emotes = {emote.name for emote in Emote.select(Emote.name)}
next_emotes = {name for name in os.listdir('static')}
new_emotes, old_emotes = next_emotes - prev_emotes, prev_emotes - next_emotes
if new_emotes:
    with db.atomic():
        Emote.bulk_create([Emote(name=name) for name in new_emotes], batch_size=100)
if old_emotes:
    with db.atomic():
        Emote.delete().where(Emote.name.in_(old_emotes)).execute()


@app.route('/', methods=['GET', 'POST'])
def main():
    emotes = Emote.select().order_by(Emote.name.asc())
    emotes = {emote.name: emote for emote in emotes}
    if request.method == 'POST':
        if len(request.form) == len(emotes):
            with db.atomic():
                for name, value in request.form.items():
                    emote = emotes.get(name)
                    if not emote:
                        continue
                    emote.set(value)
                Emote.bulk_update(emotes.values(), fields=('vote_0', 'vote_1', 'vote_2', 'vote_3'), batch_size=100)
            return redirect('/?thanks')
    if 'results' in request.args:
        emotes = sorted(emotes.items(), key=lambda e: -e[1].score)
    else:
        emotes = list(emotes.items())
        random.shuffle(emotes)
    return render_template('emotes.html', emotes=emotes)
