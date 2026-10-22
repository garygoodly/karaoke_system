import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('mfa_chars', Path(__file__).resolve().parents[1] / 'tools' / 'mfa_textgrid_to_chars.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_syllable_split():
    data = {'words': [{'text':'泡沫','start':3.63,'end':4.91}], 'phones': [
        {'text':'pʰ','start':3.63,'end':3.87}, {'text':'aw˥˩','start':3.87,'end':3.98},
        {'text':'m','start':3.98,'end':4.25}, {'text':'w','start':4.25,'end':4.37},
        {'text':'o˥˩','start':4.37,'end':4.91}]}
    r=m.convert(data,8)
    assert [(x['text'],x['start'],x['end']) for x in r['tokens']] == [('泡',11.63,11.98),('沫',11.98,12.91)]

def test_unknown_not_fabricated():
    r=m.convert({'words':[{'text':'泡沫','start':1,'end':2}], 'phones':[{'text':'spn','start':1,'end':2}]})
    assert not r['tokens'] and r['unresolved'][0]['reason']=='unknown_or_missing_phones'
