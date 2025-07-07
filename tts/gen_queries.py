import pandas as pd

"""Example cue sentences:
Condition 1: Next! Object left of the bottle on the table. To select it, gaze at the object directly
Condition 2: Next! Third object left of the bottle on the table. To select it, gaze at its pictogram"

"""

def generate_sentence(objects: list, ref: str, target: str, condition: str) -> str:
    assert ref != target, 'ref cannot be the same as target'
    scene_options = {
        1: 'Next! First object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        2: 'Next! Second object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        3: 'Next! Third object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        4: 'Next! Fourth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        5: 'Next! Fifth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        6: 'Next! Sixth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.',
        7: 'Next! Seventh object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at the object directly.'
    }
    
    screen_options = {
        1: 'Next! First object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        2: 'Next! Second object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        3: 'Next! Third object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        4: 'Next! Fourth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        5: 'Next! Fifth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        6: 'Next! Sixth object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.',
        7: 'Next! Seventh object <DIRECTION> of the <REF_OBJECT> on the table. To select it, gaze at its pictogram.'
    }
    
    ref_id = objects.index(ref)
    target_id = objects.index(target)
    
    direction = 'right' if target_id > ref_id else 'left'
    dist = abs(target_id - ref_id)
    
    # Generate cue for condition 1
    if condition == 'scene':
        sentence = scene_options[dist]
    elif condition == 'screen':
        sentence = screen_options[dist]
    else:
        raise ValueError
    
    sentence = sentence.replace('<REF_OBJECT>', ref)
    sentence = sentence.replace('<DIRECTION>', direction)
    
    return sentence
        

# Example usage
objects = [
    "bottle",
    "bandage",
    "remote",
    "can", 
    "candle", 
    "box",
    "book", 
    "cup"
]
conditions = ['scene', 'screen']

df = []
for condition in conditions:
    for ref in objects:
        for target in objects:
            if ref == target:
                continue
            else:
                sentence = generate_sentence(objects, ref, target, condition)
                df.append(
                    {
                        'ref': ref,
                        'target': target,
                        'sentence': sentence,
                        'condition': condition
                    }
                )

df = pd.DataFrame(df)
df.to_csv('queries.csv', index=False)
print("Queries generated and saved to 'queries.csv'")