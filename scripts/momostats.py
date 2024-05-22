from dataclasses import replace
import os
import re
import sys
import traceback
#import json
import argparse

from jinja2 import Environment, FileSystemLoader

import wikitextparser as wtp
import wiki

from data import load_data
from model import Character

args = None

def generate():
    global args
    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])


    total_characters = 0
    total_momotalks = 0
    total_jims=0
    memolobby_at_talk_no = [[],[],[],[],[],[],[],[],[],[],[]]
    # rank = 1
    # rental = 1
    for character in data.characters.values():
        if not character['IsPlayableCharacter'] or character['ProductionStep'] != 'Release':
            continue

        try:
            character = Character.from_data(character['Id'], data)
            #if character.club == character._club and character.club != 'Veritas': print(f' Unknown club name {character.wiki_name} {character.club}')
        except Exception as err:
            print(f'Failed to parse for DevName {character["DevName"]}: {err}')
            traceback.print_exc()
            continue
        
        #print (f"{character.dev_name.ljust(20)} {character.wiki_name}")

        #print("{{CharacterCard/sandbox|"+character.wiki_name+"|rank=|attack=|role=}}", end='')
        # print("{{CharacterCard/sandbox|"+character.wiki_name+"|rank="+str(rank)+("|rental=" if rental%5==1 else "")+"}}", end='')
        # rank +=1
        # rental +=1
        # if rank > 6: rank = 1

        
        total_characters += 1
        #print (character.momotalk.levels)
        for reward in character.momotalk.levels:
            total_momotalks += 1
            # if reward['FavorRank'] > 9:
            #     print(f"{character.wiki_name} has a reward at FavorRank {reward['FavorRank']}")
            for index,parcel in enumerate(reward['RewardParcelType']):
                if parcel == 'Currency' and reward['RewardParcelId'][index] == 3:
                    total_jims += reward['RewardAmount'][index]
            if 'MemoryLobby' in reward['RewardParcelType'] and '(' not in character.wiki_name: 
                memolobby_at_talk_no[reward['OrderInGroup']].append(character.wiki_name)


    print(f"Total playable characters: {total_characters}")
    print(f"Total momotalks: {total_momotalks}")
    print(f"Total pyroxene rewards: {total_jims}")
    print(f"Memolobbies unlock after talk no:")
    for i in range(1,11):
        print(f"{str(i).rjust(3)} - {len(memolobby_at_talk_no[i])} characters: {', '.join(memolobby_at_talk_no[i])}")


def main():
    global args

    parser = argparse.ArgumentParser()

    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')

    args = vars(parser.parse_args())
    print(args)


    try:
        generate()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()
