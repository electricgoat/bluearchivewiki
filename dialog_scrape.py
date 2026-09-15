"""Keep the dialog text the published audio pages show in place of the game data's.

The wiki's <Character>/audio pages hold transcriptions of lines the game has no text for, translations other than Global's,
corrections and translator notes. This reads each published page, matches its rows to the lines dialog.py builds from the
game data alone, and writes every Japanese or English cell saying something else to translation/audio/dialog_<Character>.json.
dialog.py shows that text in place of the game data's when it exports the page.

An empty cell, or one saying what the game data says with other line breaks or spacing, isn't kept. A line a page lists more
than once takes each cell from the first row that has one. Rows playing clips no line of the game data plays, rows laid out
other than as name, clips, Japanese, English, and repeated rows saying something else are listed.

python dialog_scrape.py -data_audio C:/blue_archive_data/datamine/blue_archive [-character_id ID ...] [-character_wikiname NAME ...] [-wiki LOGIN PASSWORD]
"""
import os
import re
import sys
import json
import traceback

import wikitextparser as wtp
from pywikiapi import Site, ApiError

import dialog
import wiki
from classes.Dialog import Dialog, Clip
from model import Character


CLIP_LINK = re.compile(r"\[\[\s*(?:File|Media)\s*:\s*([^\]|]+?)\.\w+\s*(?:\|[^\]]*)?\]\]", re.IGNORECASE)


def published_page(site, character:Character) -> str|None:
    """The wikitext of a character's published audio page; None if there is no such page."""
    try:
        return site('parse', page=f"{character.wiki_name}/audio", prop='wikitext', redirects=True)['parse']['wikitext']
    except ApiError as err:
        if 'missingtitle' in str(err): return None
        raise


def published_rows(wikitext:str) -> tuple[list[dict], list[str]]:
    """The rows of a page's dialog tables - name, clip names lowercased, Japanese and English cells - and the names of rows laid out otherwise."""
    rows, other = [], []
    for table in wtp.parse(wikitext).tables:
        for cells in table.cells(span=False):
            if any(cell.is_header for cell in cells): continue
            values = [cell.value.strip() for cell in cells]
            if len(values) != 4:
                other.append(values[0] if values else '')
                continue
            rows.append({'title': values[0], 'clips': [name.strip().replace(' ', '_').lower() for name in CLIP_LINK.findall(values[1])], 'jp': values[2], 'en': values[3]})
    return rows, other


def flat(text:str) -> str:
    """Text without whitespace, paragraph or line break markup - what it says, not how it's laid out."""
    return re.sub(r"\s+|</?p>|<br\s*/?>", '', text)


def cell_text(cell:str) -> str:
    """The text a cell shows, the way Dialog.html takes it: paragraphs apart by a blank line, line breaks as newlines."""
    text = re.sub(r"</p>\s*<p>", '\n\n', cell)
    text = re.sub(r"\s*<br\s*/?>\s*", '\n', text)
    return re.sub(r"</?p>", '', text).strip()


def scrape(character:Character, site) -> list[dict]|None:
    """The text records of the cells a character's published audio page shows differently from the game data; None if there is nothing to compare."""
    wikitext = published_page(site, character)
    if wikitext is None:
        print(f"WARNING - {character.wiki_name}/audio isn't published")
        return None

    page = dialog.collect_page(character)
    if page is None: return None

    #the lines playing each clip, by lowercased wiki name; a clip borrowed from another character also goes by the name
    #the page linked it under before, unless one of the character's own clips is named so
    lines:dict[str, list[Dialog]] = {}
    for line in page.all_lines:
        for clip in line.clips: lines.setdefault(clip.wiki_name.lower(), []).append(line)
    for line in page.all_lines:
        for clip in line.clips:
            if clip.owner is not None: lines.setdefault(Clip.name_for(character.wiki_name, clip.title).lower(), [line])

    #each line's first non-empty cells - a page listing a line twice lists it first in the table the line is still in
    rows, other = published_rows(wikitext)
    cells:dict[int, dict[str, str]] = {}
    unmatched, conflicts = [], []
    for row in rows:
        matches = {id(line) for name in row['clips'] for line in lines.get(name, [])}
        if len(matches) != 1:
            unmatched.append(f"{row['title']} ({', '.join(row['clips']) or 'no clips'})")
            continue

        line_cells = cells.setdefault(matches.pop(), {})
        for field, cell in (('LocalizeJP', row['jp']), ('LocalizeEN', row['en'])):
            if flat(cell) and flat(line_cells.setdefault(field, cell)) != flat(cell): conflicts.append(f"{row['title']} {field}")

    records = []
    for line in page.all_lines:
        if id(line) not in cells: continue
        record = {'CharacterId': character.id, 'DialogCategory': line.dialog_category, 'VoiceClip': line.clips[0].wiki_name, 'Path': line.clips[0].path}
        for field, official in (('LocalizeJP', line.wiki_localization_jp), ('LocalizeEN', line.wiki_localization_en)):
            cell = cells[id(line)].get(field)
            if cell is not None and flat(cell) != flat(official): record[field] = cell_text(cell)
        if 'LocalizeJP' in record or 'LocalizeEN' in record: records.append(record)

    print(f"{character.wiki_name}/audio: {len(rows) - len(unmatched)} of {len(rows)} rows matched, text kept for {len(records)} lines ({sum('LocalizeJP' in x for x in records)} Japanese, {sum('LocalizeEN' in x for x in records)} English)")
    if unmatched: print(f"WARNING - rows playing clips of no line or of several, not kept: {unmatched}")
    if other: print(f"WARNING - rows not laid out as name, clips, Japanese, English, not kept: {other}")
    if conflicts: print(f"WARNING - lines listed again with other text, the first row's kept: {conflicts}")
    return records


def write_records(character:Character, records:list[dict]):
    """Write a character's text records to translation/audio, or remove its file when there are none."""
    path = os.path.join(dialog.args['translation'], 'audio', f"dialog_{character.wiki_name.replace(' ', '_')}.json")

    if not records:
        if os.path.exists(path): os.remove(path)
        return

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding="utf8") as f:
        f.write(json.dumps({'DataList': records}, sort_keys=False, indent=4, ensure_ascii=False) + "\n")


def main():
    dialog.init(vars(dialog.argument_parser().parse_args()))
    site = wiki.site if wiki.site is not None else Site(wiki.WIKI_API) #reading pages needs no login

    failed = []
    for character in dialog.selected_characters():
        #a failure with one character is reported, and scraping carries on with the next
        try:
            records = scrape(character, site)
            if records is not None: write_records(character, records)
        except Exception as err:
            print(f"ERROR - scraping [{character.id}] {character.wiki_name} failed: {err}")
            traceback.print_exc()
            failed.append(f"[{character.id}] {character.wiki_name}")

    if failed:
        print(f"ERROR - {len(failed)} characters failed to scrape: {', '.join(failed)}")
        sys.exit(1)


if __name__ == '__main__':
    main()
