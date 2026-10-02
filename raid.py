import os
import traceback
import argparse

import wiki

from jinja2 import Environment, FileSystemLoader
from data import load_data, load_season_data
from raid_seasons import prepare_seasons
import raid_rewards
import shared.functions
from shared.MissingTranslations import MissingTranslations
from shared.standard_dictionaries import build_standard_dictionaries

MODE = raid_rewards.TOTAL_ASSAULT

args = {}

characters = {}
items = {}
furniture = {}
emblems = {}

season_data = {}
missing_localization = MissingTranslations("translation/missing/LocalizeExcelTable.json")
missing_skill_localization = MissingTranslations("translation/missing/LocalizeSkillExcelTable.json")
missing_code_localization = MissingTranslations("translation/missing/LocalizeCodeExcelTable.json")
missing_etc_localization = MissingTranslations("translation/missing/LocalizeEtcExcelTable.json")



def wiki_card(type: str, id: int, **params):
    global data, characters, items, furniture, emblems
    return shared.functions.wiki_card(type, id, data=data, characters=characters, items=items, furniture=furniture, emblems=emblems, **params)



def get_raid_boss_data(group):
    global args, data, season_data
    global missing_skill_localization
    global missing_etc_localization

    boss_data = {}

    boss_data['stage'] = data.raid_stage[group]
    for stage in boss_data['stage']:
        #print (f"RaidCharacterId: {stage['RaidCharacterId']} {stage['RaidBossGroup']} {stage['Difficulty']}")
        stage['ground'] = data.ground[stage['GroundId']]
        stage['character'] = data.characters[stage['RaidCharacterId']]
        stage['characters_stats'] = data.characters_stats[stage['RaidCharacterId']]
        stage['character_skills'] = get_boss_skills(data.costumes[data.characters[stage['RaidCharacterId']]['CostumeGroupId']]['CharacterSkillListGroupId'], data, missing_skill_localization)

        stage['boss_characters'] = [data.characters[x] for x in stage['BossCharacterId']]
        stage['boss_characters_stats'] = [data.characters_stats[x] for x in stage['BossCharacterId']]
        stage['boss_characters_skills'] = [get_boss_skills(data.costumes[data.characters[x]['CostumeGroupId']]['CharacterSkillListGroupId'], data, missing_skill_localization) for x in stage['BossCharacterId']]

        for boss_character in stage['boss_characters']:
            boss_character['localization'] = data.etc_localization.get(boss_character['LocalizeEtcId'])
            if 'NameEn' not in boss_character['localization'] and boss_character['localization'].get('NameJp', "") != "":
                missing_etc_localization.add_entry(boss_character['localization'])
    
    return boss_data



def get_boss_skills(skill_list_group_id, data, missing_skill_localization):

    SKILL_LISTS = {'NormalSkillGroupId':'Normal', 'ExSkillGroupId':'EX', 'PublicSkillGroupId':'Public', 'PassiveSkillGroupId':'Passive', 'LeaderSkillGroupId':'Leader', 'ExtraPassiveSkillGroupId':'Sub', 'HiddenPassiveSkillGroupId':'Hidden'}

    skill_list_group = data.characters_skills[(skill_list_group_id, 0, 0, 0)]
    if data.characters_skills.get((skill_list_group_id, 0, 0, 1), False): #Collate FormIndex0 and FormIndex1 skills, todo figure out a better way
        skill_list_group_fi1 = data.characters_skills[(skill_list_group_id, 0, 0, 1)]
        # print(f"Found FormIndex 1 for {skill_list_group_id}")
        # print (f"{skill_list_group['PassiveSkillGroupId']}")
        # print (f"{skill_list_group_fi1['PassiveSkillGroupId']}")
        for skill_group in SKILL_LISTS.keys():
            for f1gid in skill_list_group_fi1[skill_group]:
                if f1gid not in skill_list_group[skill_group]:
                    skill_list_group[skill_group].append(f1gid)

    
    #skills appear to be referenced by GroupId rather than Id, so prepare a better data structure
    skills_by_groupid = {item['GroupId']: item for item in data.skills.values()}

    # skill_data = [
    #     {
    #         **skills_by_groupid[skill_id], 
    #         'SkillType': SKILL_LISTS[skill_group],
    #         'IconName': skills_by_groupid[skill_id]['IconName'][skills_by_groupid[skill_id]['IconName'].rfind('/') + 1:]
    #     }
    #     for skill_group in SKILL_LISTS.keys()
    #     for skill_id in skill_list_group[skill_group]
    # ]

    skill_data = []
    for skill_group in SKILL_LISTS.keys():
        for skill_id in skill_list_group[skill_group]:
            skill = skills_by_groupid[skill_id]
            if skill['IsShowInfo']:
                skill_data.append({
                    **skill, 
                    'SkillType': SKILL_LISTS[skill_group],
                    'IconName': skill['IconName'][skill['IconName'].rfind('/') + 1:]
                })
            if skill['AdditionalToolTipId'] != 0: 
                for add_tooltip in data.skill_additional_tooltip.get(skill['AdditionalToolTipId'], []):
                    add_skill = skills_by_groupid[add_tooltip['AdditionalSkillGroupId']]
                    skill_data.append({
                        **add_skill, 
                        'SkillType': SKILL_LISTS[skill_group] + ' tooltip',
                        'IconName': add_skill['IconName'][add_skill['IconName'].rfind('/') + 1:]
                    })


    for skill in skill_data:
        loc_data = data.skills_localization[skill['LocalizeSkillId']]
        if 'NameEn' not in loc_data and loc_data.get('NameJp', "") != "":
            missing_skill_localization.add_entry(loc_data)

    return skill_data



def generate():
    global args, data, season_data
    global missing_code_localization

    boss_groups = ['OpenRaidBossGroup']
    boss_data = {}

    env = Environment(loader=FileSystemLoader(os.path.dirname(__file__)))
    env.filters['environment_type'] = shared.functions.environment_type
    env.filters['damage_type'] = shared.functions.damage_type
    env.filters['armor_type'] = shared.functions.armor_type
    env.filters['thousands'] = shared.functions.format_thousands
    env.filters['ms_duration'] = shared.functions.format_ms_duration
    env.filters['colorize'] = shared.functions.colorize
    env.filters['nl2br'] = shared.functions.nl2br
    

    seasons = raid_rewards.seasons_as_ran(MODE, prepare_seasons(season_data['jp'].raid_season, 'jp'), args['translation'])
    seasons = raid_rewards.global_seasons(seasons, prepare_seasons(season_data['gl'].raid_season, 'gl'), season_data['gl'].raid_ranking_reward)
    rewards ={x['SeasonId']: raid_rewards.season_rewards(x, data.raid_ranking_reward, data.raid_stage_season_reward, wiki_card) for x in seasons}
    rewards_wikitexts = raid_rewards.rewards_pages(MODE, seasons, rewards, env)

    os.makedirs(os.path.join(args['outdir'], 'raids'), exist_ok=True)
    for season in seasons:
        print (f"Working on season {season['SeasonId']}")
        wikitext = "\n==Boss Info==\n===Stats===\n"        

        template = env.get_template('./raid/template_raid_boss.txt')
        for group in boss_groups:
            boss_data[season[group][0]]= get_raid_boss_data(season[group][0])

            durations = '/'.join(set([shared.functions.format_ms_duration(stage['BattleDuration']) for stage in boss_data[season[group][0]]['stage']]))
            wikitext += f"Battle time for this boss is {durations}.\n"
            wikitext += template.render(season_data=season, boss_data=boss_data[season[group][0]])
 
            template = env.get_template('./raid/template_boss_skilltable.txt')
            skilltables = {stage['Difficulty']:template.render(stage=stage, skills_localization = data.skills_localization) for stage in boss_data[season[group][0]]['stage']}
            template = env.get_template('./raid/template_boss_skills.txt')
            wikitext += template.render(skilltables=shared.functions.deduplicate_dict_values(skilltables))


        wikitext += "==Unit recommendations==\n"
        wikitext += MODE.section
        wikitext += "\n\n[[Category:Raid boss]]"

        
        localization_id = boss_data[season[group][0]]['stage'][0]['BossBGInfoKey']
        #print(f"localize_code id is {localization_id}")
        try:
            blurb = 'En' in data.localize_code[localization_id] and data.localize_code[localization_id]['En'] or data.localize_code[localization_id]['Jp']
        except:
            blurb = ''
            if localization_id in data.localize_code: missing_code_localization.add_entry(data.localize_code[localization_id])
        template = env.get_template('./raid/template_raid_intro.txt')
        wikitext = template.render(info=season['raid'], blurb=blurb, season_data=season) + wikitext


        with open(os.path.join(args['outdir'], 'raids' ,f"raid_season_{season['SeasonId']}.txt"), 'w+', encoding="utf8") as f:
            f.write(wikitext)

        boss_name = season['raid'].shortname.replace(' ', '_')
        with open(os.path.join(args['outdir'], 'raids' ,f"rewards_{boss_name}_season_{season['SeasonId']:02d} ({season['SeasonDisplay']}).txt"), 'w+', encoding="utf8") as f:
            f.write(rewards_wikitexts[season['SeasonId']])
 
    if wiki.site != None:
        raid_rewards.publish(MODE, seasons, rewards_wikitexts, args)



def init_data():
    global args, data, season_data
    global characters, items, furniture, emblems

    data = load_data(args['data_primary'], args['data_secondary'], args['translation'])
    season_data['jp'] = load_season_data(args['data_primary'])
    season_data['gl'] = load_season_data(args['data_secondary'])

    characters, items, furniture, emblems = build_standard_dictionaries(data, missing_localization, missing_etc_localization)


def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('-data_primary',    metavar='DIR', default='../ba-data/jp',     help='Fullest (JP) game version data')
    parser.add_argument('-data_secondary',  metavar='DIR', default='../ba-data/global', help='Secondary (Global) version data to include localisation from')
    parser.add_argument('-translation',     metavar='DIR', default='../bluearchivewiki/translation', help='Additional translations directory')
    parser.add_argument('-outdir',          metavar='DIR', default='out', help='Output directory')
    parser.add_argument('-wiki', nargs=2, metavar=('LOGIN', 'PASSWORD'), help='Publish the rewards pages of the current and previous seasons, and purge their raids\' pages to show them')
    parser.add_argument('-season_id', type=int, nargs='+', metavar='ID', help='Seasons to publish instead, by SeasonId')
    parser.add_argument('-all_seasons', action='store_true', help='Publish every season instead')

    args = vars(parser.parse_args())
    print(args)

    if args['wiki'] != None:
        wiki.init(args)
    else:
        args['wiki'] = None

    try:
        init_data()
        generate()
        missing_localization.write()
        missing_skill_localization.write()
        missing_code_localization.write()
        missing_etc_localization.write()
    except:
        parser.print_help()
        traceback.print_exc()


if __name__ == '__main__':
    main()

