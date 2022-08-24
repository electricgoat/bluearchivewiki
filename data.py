import collections
import json
import os

BlueArchiveData = collections.namedtuple(
    'BlueArchiveData',
    ['characters', 'characters_ai', 'characters_localization', 'characters_skills', 'characters_stats', 'characters_cafe_tags', 
    'skills', 'skills_localization','translated_characters','translated_skills',
    'weapons', 'translated_weapons', 'gear',
    'currencies','translated_currencies',
    'items', #'translated_items',
    'recipes', 'recipes_ingredients', 
    'favor_levels', 'favor_rewards', 
    'memory_lobby','etc_localization',
    'character_dialog','character_dialog_event',
    'scenario_script_favor','levelskill' ,'logiceffectdata']
)


def load_data(path_primary, path_secondary, path_translation):
    return BlueArchiveData(
        characters=load_characters(path_primary),
        characters_ai=load_characters_ai(path_primary),
        characters_localization=load_characters_localization(path_primary),
        characters_skills=load_characters_skills(path_primary),
        characters_stats=load_characters_stats(path_primary),
        characters_cafe_tags = load_characters_cafe_tags(path_primary),
        skills=load_skills(path_primary),
        skills_localization=load_skills_localization(path_primary),
        translated_characters = load_characters_translation(path_translation),
        translated_skills =  load_skills_translation(path_translation),
        weapons = load_weapons(path_primary),
        translated_weapons = load_weapons_translation(path_translation),
        gear = load_gear(path_primary),
        currencies=load_currencies(path_primary),
        translated_currencies=load_currencies_translation(path_translation),
        items=load_items(path_primary),
        #translated_items=load_items_translation(path_translation),
        recipes=load_recipes(path_primary),
        recipes_ingredients=load_recipes_ingredients(path_primary),
        favor_levels=load_favor_levels(path_primary),
        favor_rewards=load_favor_rewards(path_primary),
        memory_lobby=load_memory_lobby(path_primary),
        etc_localization=load_etc_localization(path_primary, path_secondary, path_translation),
        character_dialog=load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogExcelTable.json'),
        character_dialog_event=load_character_dialog(path_primary, path_secondary, path_translation, 'CharacterDialogEventExcelTable.json'),
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation),
        levelskill = load_levelskill(path_primary),
        logiceffectdata = load_skill_logiceffectdata(path_primary)
    )


def load_characters(path):
    return load_file(os.path.join(path, 'Excel', 'CharacterExcelTable.json'))


def load_characters_ai(path):
    return load_file(os.path.join(path, 'Excel', 'CharacterAIExcelTable.json'))


def load_characters_localization(path):
    return load_file(os.path.join(path, 'Excel', 'LocalizeCharProfileExcelTable.json'), key='CharacterId')


def load_characters_skills(path):
    with open(os.path.join(path, 'Excel', 'CharacterSkillListExcelTable.json')) as f:
        data = json.load(f)

    return {
        (character_skill['CharacterId'], character_skill['MinimumGradeCharacterWeapon'], character_skill["MinimumTierCharacterGear"], character_skill['IsFormConversion']): character_skill
        for character_skill
        in data['DataList']
    }


def load_characters_stats(path):
    return load_file(os.path.join(path, 'Excel', 'CharacterStatExcelTable.json'), key='CharacterId')


def load_currencies(path):
    return load_file(os.path.join(path, 'Excel', 'CurrencyExcelTable.json'), key='ID')


def load_file(file, key='Id'):
    with open(file,encoding="utf8") as f:
        data = json.load(f)

    return {item[key]: item for item in data['DataList']}


def load_items(path):
    return load_file(os.path.join(path, 'Excel', 'ItemExcelTable.json'))

def load_recipes(path):
    return load_file(os.path.join(path, 'Excel', 'RecipeExcelTable.json'))

def load_recipes_ingredients(path):
    return load_file(os.path.join(path, 'Excel', 'RecipeIngredientExcelTable.json'))

def load_skills(path):
    return load_file(os.path.join(path, 'Excel', 'SkillExcelTable.json'))

def load_skills_localization(path):
    return load_file(os.path.join(path, 'Excel', 'LocalizeSkillExcelTable.json'), key='Key')

def load_characters_translation(path):
    return load_file(os.path.join(path, 'CharProfile.json'), key='CharacterId')

def load_weapons(path):
    return load_file(os.path.join(path, 'Excel', 'CharacterWeaponExcelTable.json'), key='Id')

def load_weapons_translation(path):
    return load_file(os.path.join(path, 'Weapons.json'), key='Id')

def load_gear(path):
    with open(os.path.join(path, 'Excel', 'CharacterGearExcelTable.json')) as f:
        data = json.load(f)
        f.close()

    return {
        (gear['CharacterId'], gear['Tier']): gear
        for gear
        in data['DataList']
    }

def load_favor_levels(path):
    with open(os.path.join(path, 'Excel', 'FavorLevelRewardExcelTable.json')) as f:
        data = json.load(f)
        f.close()

    return {
        (favor_level['CharacterId'], favor_level['FavorLevel']): favor_level
        for favor_level
        in data['DataList']
    }

def load_favor_rewards(path):
    with open(os.path.join(path, 'Excel', 'AcademyFavorScheduleExcelTable.json')) as f:
        data = json.load(f)
        f.close()

    return {
        (favor_rewards['CharacterId'], favor_rewards['FavorRank']): favor_rewards
        for favor_rewards
        in data['DataList']
    }
  

def load_memory_lobby(path):
    return load_file(os.path.join(path, 'Excel', 'MemoryLobbyExcelTable.json'), key='CharacterId')

def load_currencies_translation(path):
    return load_file(os.path.join(path, 'Currencies.json'))

# def load_items_translation(path):
#     return load_file(os.path.join(path, 'Items.json'))

def load_skills_translation(path):
    return load_file(os.path.join(path, 'Skills.json'), key='GroupId')

def load_characters_cafe_tags(path):
    return load_file(os.path.join(path, 'Excel', 'CharacterAcademyTagsExcelTable.json'))

def load_etc_localization(path_primary, path_secondary, translation):
    data_primary = load_file(os.path.join(path_primary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_secondary = load_file(os.path.join(path_secondary, 'Excel', 'LocalizeEtcExcelTable.json'), key='Key')
    data_aux = None

    index_list = list(data_primary.keys())
    index_list.extend(x for x in list(data_secondary.keys()) if x not in index_list)

    if os.path.exists(os.path.join(translation, 'LocalizeEtcExcelTable.json')):
        print(f'Loading additional translations from {translation}/LocalizeEtcExcelTable.json')
        data_aux = load_file(os.path.join(translation, 'LocalizeEtcExcelTable.json'))

        index_list.extend(x for x in list(data_aux.keys()) if x not in index_list)

    for index in index_list:
        try: 
            if data_aux != None and index in data_aux:
                #print(f'Loading aux translation {index}')
                data_primary[index] = data_aux[index] 
            else :
                #print(f'Loading secondary data translation {index}')
                data_primary[index] = data_secondary[index] 
        except KeyError:
            #print (f'No secondary data for localize item {index}')
            continue
    
    return data_primary


def load_character_dialog(path_primary, path_secondary, path_translation,  filename):
    #dp = {}
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'Excel', filename), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']

    with open(os.path.join(path_secondary, 'Excel', filename), encoding="utf8") as f:
        data_secondary = json.load(f)['DataList']

    for file in os.listdir(path_translation + '/audio/'):
        if not file.endswith('.json'):
            continue

        #print(f'Loading additional audio translations from {path_translation}/audio/{file}')
        with open(os.path.join(path_translation + '/audio/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']
    

    for line in data_secondary:
        ds[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])] = line 

    for line in data_aux:
        da[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])] = line 

    for line in data_primary:
        try: 
            
            if (line['CharacterId'], line['DialogCategory'], line['LocalizeJP']) in da: line['LocalizeEN'] = da[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]['LocalizeEN']
            elif (line['CharacterId'], line['DialogCategory'], line['LocalizeJP']) in ds: line['LocalizeEN'] = ds[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]['LocalizeEN']
            elif 'LocalizeEN' not in line: line['LocalizeEN'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['CharacterId'], line['DialogCategory'], line['LocalizeJP'])]}")
            line['LocalizeEN'] = ''
            pass

        data.append(line)

    return data


def load_levelskill(path):
    data = {}
    for file in os.listdir(path + '/LevelSkill/'):
        if not file.endswith('.json'):
            continue

        with open(os.path.join(path + '/LevelSkill/', file), encoding="utf8") as f:
            skill_info = json.load(f)
            data[skill_info[0]['GroupName']] = skill_info[0]

    return data


def load_skill_logiceffectdata(path):
    with open(os.path.join(path, 'Battle', 'logiceffectdata.json'), encoding="utf8") as f:
        data = json.load(f)

    return {item['StringId']: item for item in data}







BlueArchiveScenarioData = collections.namedtuple(
    'BlueArchiveScenarioData',
    ['scenario_script_favor']
)


def load_scenario_data(path_primary, path_secondary, path_translation):
    return BlueArchiveScenarioData(
        scenario_script_favor=load_scenario_script_favor(path_primary, path_secondary, path_translation)
    )


def load_scenario_script_favor(path_primary, path_secondary, path_translation):
    data = []
    #data['DataList'] = []

    for i in range(1,3): data += load_scenario_script_favor_part(path_primary, path_secondary, path_translation, i)

    return data


def load_scenario_script_favor_part(path_primary, path_secondary, path_translation, part):
    ds = {}
    da = {}
    data = []
    data_aux = []

    with open(os.path.join(path_primary, 'Excel', f'ScenarioScriptFavor{part}ExcelTable.json'), encoding="utf8") as f:
        data_primary = json.load(f)['DataList']
        #print(f'Loaded primary script data from ScenarioScriptFavor{part}ExcelTable.json, {len(data_primary)} entries')

    with open(os.path.join(path_secondary, 'Excel', f'ScenarioScriptFavor{part}ExcelTable.json'), encoding="utf8") as f:
        data_secondary = json.load(f)['DataList']
        #print(f'Loaded secondary script data from ScenarioScriptFavor{part}ExcelTable.json, {len(data_primary)} entries')

    for file in os.listdir(path_translation + '/scenario/'):
        if not file.endswith('.json'):
            continue

        #print(f'Loading additional scenario translations from {path_translation}/scenario/{file}')
        with open(os.path.join(path_translation + '/scenario/', file), encoding="utf8") as f:
            data_aux += json.load(f)['DataList']

    for line in data_secondary:
        ds[(line['GroupId'], line['ScriptKr'], line['TextJp'])] = line 

    for line in data_aux:
        da[(line['GroupId'], line['ScriptKr'], line['TextJp'])] = line 

    for line in data_primary:
        try: 
            
            if (line['GroupId'], line['ScriptKr'], line['TextJp']) in da: line['TextEn'] = da[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif (line['GroupId'], line['ScriptKr'], line['TextJp']) in ds: line['TextEn'] = ds[(line['GroupId'], line['ScriptKr'], line['TextJp'])]['TextEn']
            elif 'TextEn' not in line: line['TextEn'] = ''

        except KeyError:
            #print (f"Localization not found {dp[(line['GroupId'], line['ScriptKr'], line['TextJp'])]}")
            line['TextEn'] = ''
            pass

        data.append(line)

    return data