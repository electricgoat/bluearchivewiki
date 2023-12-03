import json

class MissingTranslations:
    def __init__(self, filename):
        self.filename = filename
        self.entries = []


    def add_entry(self, value):
        if self.__is_new(value): 
            self.entries.append(value)
            return True
        else:
            return False


    def write(self):
        if self.entries:
            self.__add_empty_en_fields()
            with open(self.filename, 'w', encoding="utf8") as file:
                file.write(json.dumps({'DataList': self.entries}, sort_keys=False, indent=4, ensure_ascii=False))
                file.close()
            print(f"Dumped missing localizations to {self.filename}")
        else:
            print(f"No missing localizations to write for {self.filename}")


    def __add_empty_en_fields(self):
        keys_to_add = []
        for entry in self.entries:
            for key, value in entry.items():
                if key.endswith("Jp"):
                    en_key = key[:-2] + "En"  # Replace "Jp" with "En"
                    if en_key not in entry:
                        keys_to_add.append(en_key)

            for en_key in keys_to_add:
                entry[en_key] = ""


    def __is_new(self, newentry):
        for entry in self.entries:
            if newentry['Key'] == entry['Key']:
                return False
        return True
