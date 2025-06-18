import pandas as pd


def generate_sentence(objects: list, ref: str, target: str) -> str:
    assert ref != target, 'ref cannot be the same as target'
    options = {
        1: 'Select the object to the <DIRECTION> of <REF_OBJECT>.',
        2: 'Select the second object to the <DIRECTION> of <REF_OBJECT>.',
        3: 'Select the third object to the <DIRECTION> of <REF_OBJECT>.',
        4: 'Select the fourth object to the <DIRECTION> of <REF_OBJECT>.',
        5: 'Select the fifth object to the <DIRECTION> of <REF_OBJECT>.',
        6: 'Select the sixth object to the <DIRECTION> of <REF_OBJECT>.',
        7: 'Select the seventh object to the <DIRECTION> of <REF_OBJECT>.'
    }
    
    ref_id = objects.index(ref)
    target_id = objects.index(target)
    
    direction = 'right' if target_id > ref_id else 'left'
    dist = abs(target_id - ref_id)
    sentence = options[dist]
    sentence = sentence.replace('<REF_OBJECT>', ref)
    sentence = sentence.replace('<DIRECTION>', direction)
    
    return sentence
        

# Example usage
objects = [
    "red-cup",
    "white-gauze",
    "plastic-tube",
    "tin-box", 
    "red-candle", 
    "medicine-box",
    "blue-book", 
    "black-cup"
]

df = []
for ref in objects:
    for target in objects:
        if ref == target:
            continue
        else:
            sentence = generate_sentence(objects, ref, target)
            df.append({
                'ref': ref,
                'target': target,
                'sentence': sentence
            })
            
df = pd.DataFrame(df)
df.to_csv('queries.csv', index=False)
print("Queries generated and saved to 'queries.csv'")