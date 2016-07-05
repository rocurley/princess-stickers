#!/usr/bin/env python

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    InlineQueryHandler,
    )
from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
)
import telegram

import sqlite3

import marisa_trie

import logging
logging.basicConfig(level=logging.DEBUG,
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
with open("token", "r") as fin:
    token = fin.read().strip()

upload_chat_id = ""

moods =['lonely',
 'pressured',
 'depressed',
 'angry',
 'yielding',
 'cheerful',
 'neutral',
 'afraid',
 'willful']

mood_synonyms = \
    { "sad"          : "depressed"
    , "happy"        : "cheerful"
    , "stressed"     : "pressured"
    , "scared"       : "afraid"
    }

outfits = ['faith',
 'agility',
 'animals',
 'economics',
 'weapons',
 'conversation',
 'royal_demeanour',
 'lumen',
 'military',
 'medicine',
 'art',
 'athletics',
 'boarding_school',
 'intrigue',
 'history']

outfit_synonyms = \
    { "queen"        : "royal_demeanour"
    , "magical_girl" : "lumen"
    , "uniform"      : "military"
    , "tutu"         : "agility"
    , "tophat"       : "economics"
    , "suit"         : "economics"
    , "tea_dress"    : "conversation"
    , "catsuit"      : "intrigue"
    , "nurses_gown"  : "medicine"
    , "school"       : "boarding_school"
    , "sports"       : "athletics"
    }

def normalize(str):
    return unicode(str.lower().replace("_","").replace("-",""))

moods_trie = marisa_trie.BytesTrie(
    [(normalize(x),x) for x in moods] +
    [(normalize(k),v) for (k,v) in mood_synonyms.iteritems()])

outfits_trie = marisa_trie.BytesTrie(
    [(normalize(x),x) for x in outfits] +
    [(normalize(k),v) for (k,v) in outfit_synonyms.iteritems()])

def get_sticker_id(conn,outfit,mood):
    c = conn.cursor()
    c.execute("SELECT file_id FROM stickers WHERE outfit=? AND mood=?",(outfit,mood))
    result = c.fetchone()
    if result:
        return result[0].encode("ascii")

def load_sticker(conn,bot,update,outfit,mood):
    c = conn.cursor()
    m = bot.sendSticker(update.message.chat_id,
                        open('./%s/%s.webp'%(outfit,mood), 'rb'))
    file_id = m.sticker.file_id
    c.execute("INSERT INTO stickers VALUES (?,?,?)", (outfit,mood,file_id))
    conn.commit()

def parse_query(query,conn):
    if not query:
        return
    words = query.split()
    logging.debug(words)
    if len(words) == 1:
        for outfit in list(set(x for (_,x) in outfits_trie.items(words[0]))):
            for mood in moods:
                yield (outfit,mood)
        for mood in list(set(x for (_,x) in moods_trie.items(words[0]))):
            for outfit in outfits:
                yield (outfit,mood)
    if len(words) == 2:
        for outfit in list(set(x for (_,x) in outfits_trie.items(words[0]))):
            for mood in list(set(x for (_,x) in moods_trie.items(words[1]))):
                yield (outfit,mood)

def inline_stickers(bot, update):
    conn = sqlite3.connect('stickers.db')
    query = update.inline_query.query
    results = []
    for (outfit,mood) in parse_query(query,conn):
        sticker_id = get_sticker_id(conn,outfit,mood)
        logging.debug(sticker_id)
        if sticker_id:
            results.append(
                telegram.InlineQueryResultCachedSticker(
                id="%s,%s"%(outfit,mood),
                sticker_file_id=sticker_id
                )
            )
    logging.debug(bot.answerInlineQuery(update.inline_query.id
                                       , results
                                       , cache_time = 0))
    conn.close()

def register(bot, update):
    global upload_chat_id
    upload_chat_id = update.message.chat_id
    bot.sendMessage(update.message.chat_id,text="Confirmed.")

def init(bot,update):
    conn = sqlite3.connect('stickers.db')
    for outfit in outfits:
        for mood in moods:
            if not get_sticker_id(conn,outfit,mood):
                load_sticker(conn,bot,update,outfit,mood)
    bot.sendMessage(update.message.chat_id,text="Done.")
    conn.close()

updater = Updater(token)

#updater.dispatcher.add_handler(CommandHandler("register", register))
updater.dispatcher.add_handler(CommandHandler("init", init))
updater.dispatcher.add_handler(InlineQueryHandler(inline_stickers))

updater.start_polling()
updater.idle()

