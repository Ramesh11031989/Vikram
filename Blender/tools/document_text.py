"""Hand-typeset Devanagari text for the evidence props (no Blender needed).

Every string is final close-up text. Do not generate or auto-correct it.
"""

SENTENCE = 'पानी सीढ़ियाँ गिनता हुआ चढ़ा।'  # identical on all seven statements

# (page, witness, hand index, header, lines). Page 1 is the halwai, page 7 is Gopal.
STATEMENTS = (
    (1, 'हलवाई', 0, 'हलवाई का बयान', ('मैं छत पर था।', SENTENCE)),
    (2, 'पड़ोसन', 1, 'पड़ोसन का बयान', ('मैं मवेशी खोल रही थी।', SENTENCE)),
    (3, 'लड़का', 2, 'घंटी सुनने वाले लड़के का बयान', ('मैंने घंटी सुनी।', SENTENCE)),
    (4, 'मौसी', 3, 'लड़के की मौसी का बयान', ('मैं ढलान पर बैठी थी।', SENTENCE)),
    (5, 'कालू', 0, 'कालू का बयान', ('मैं ढलान पर था।', SENTENCE)),
    (6, 'बिरजू', 1, 'बिरजू का बयान', ('मैं ढलान पर था।', SENTENCE)),
    (7, 'गोपाल', 2, 'गोपाल का बयान', ('मैं नाव में था।', SENTENCE)),
)

ARRIVAL_TITLE = 'शरण-सूची: आने का क्रम'
ARRIVAL_HEAD = ('क्रम', 'नाम')
# Gopal is third; the halwai and the neighbour share line 2; all seven witnesses appear.
ARRIVAL = (
    ('१', 'लड़का (घंटी वाला)'),
    ('२', 'हलवाई और उसकी पड़ोसन'),
    ('३', 'गोपाल (नाविक)'),
    ('४', 'लड़के की मौसी'),
    ('५', 'कालू'),
    ('६', 'बिरजू'),
    ('७', 'एक परिवार (चार जन)'),
)
ARRIVAL_FOOT = 'श्मशान की ढलान, बेताल और दो नाविकों ने लिखा'

ORDER_TITLE = 'आदेश'
ORDER_BODY = ('फाटक के रखवाले नंदू को बंदी बनाया जाए।',
              'सात लोगों की गवाही है कि उसने फाटक उठाया।')
ORDER_RETURN = ('फाटक पर नंदू की पहचान के समर्थन में जिन सात बयानों का मैंने',
                'हवाला दिया था, वे एक ही आदमी के देखे लाल कपड़े पर टिके हैं।',
                'नंदू को बंदी बनाने का अपना आदेश मैं वापस लेता हूँ।')
ORDER_SEAL = 'विक्रम'

TALLY_TITLE = 'मोहल्लावार मृतक-गणना'
# (mohalla, count). None is the blank box. Do not write a zero in it.
TALLY = (
    ('कुम्हारटोला', '४'),
    ('अनाज मंडी', '९'),
    ('घाट-टोला', '८'),
    ('पीपलघाट', None),
    ('ऊपरी बस्ती', '६'),
)
TALLY_TOTAL = 'नगर में कुल मृतक — २७'
TALLY_BLANK_ROW = 3

DECREE_TITLE = 'राजादेश'
DECREE_BODY = ('गिनती की सीमा: मृतकों की गिनती उसी मोहल्ले तक',
               'मानी जाएगी जिसका हाल मिल चुका हो।',
               'जिसकी ख़बर न आई हो, उसके आगे ख़ाली खाना रहेगा।')
DECREE_SEAL = ORDER_SEAL  # the same royal seal on both papers

LEDGER_TITLE = 'राजकीय बही'
LEDGER_TORN = 'फटे पन्ने'
