import numpy as np
import pytest
from app.preprocessing import normalize_text
from app.postprocessing import make_prediction


def test_normalization_preserves_zwnj():
    assert normalize_text('  مي\u200cروم   خانه\n  ') == 'می\u200cروم خانه'
    assert normalize_text('كتاب') == 'کتاب'
    assert normalize_text('نمی‌روم') == 'نمی‌روم'
    assert normalize_text('دوست ندارم!') == 'دوست ندارم!'
    with pytest.raises(ValueError):
        normalize_text('  ')


def test_postprocessing_probabilities():
    r = make_prediction('sentiment', np.array([1, 1, 3]), ['Negative', 'Neutral', 'Positive'], {'repo':'test','revision':'abc'})
    assert r['label'] == 'positive'
    assert r['label_fa'] == 'مثبت'
    assert abs(sum(x['score'] for x in r['scores']) - 1) < 0.00001
    assert not r['confidence_calibrated']
    with pytest.raises(ValueError):
        make_prediction('sentiment', np.array([np.nan, 1, 3]), ['Negative','Neutral','Positive'], {'repo':'x','revision':'y'})


def test_topic_label_mapping():
    labels=['اجتماعی','اقتصادی','بین الملل','سیاسی','علمی فناوری','فرهنگی هنری','ورزشی','پزشکی']
    r=make_prediction('topics',[0,5,0,0,0,0,0,0],labels,{'repo':'x','revision':'y'})
    assert r['label'] == 'economics'
    assert r['label_fa'] == 'اقتصادی'
