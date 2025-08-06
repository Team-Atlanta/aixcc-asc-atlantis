from .test_lang import TestLang, Field

def check_semantic_validity(lang: TestLang) -> str:
    for _, record in lang.records.items():
        for field in record.fields:
            if field.type == Field.Record or field.type == Field.Array:
                if field.name not in lang.records:
                    return f'unknown record "{field.name}" has not been defined'
            
    return None

