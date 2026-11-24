# सहायक: शरण-सूची बनाने वाले दो नाविक

ढलान पर बेताल के साथ आए लोगों के नाम दर्ज करने वाले दो नाविक। ये मॉडल तभी काम आते हैं जब पिछली रात दिखाई जाए। कहानी इनका लिंग, आपसी रिश्ता या नाम तय नहीं करती, इसलिए मॉडल भी कुछ तय नहीं करते। दोनों गोपाल नहीं हैं। दोनों नागरिक रिग (34 हड्डियाँ, वही चेहरा और मुँह के phoneme shapes) पर बने हैं और नाविक पोशाक पहनते हैं।

| | नाविक A (`SailorA`) | नाविक B (`SailorB`) |
| --- | --- | --- |
| क़द | लगभग 1.76 m, दुबला | लगभग 1.67 m, ठोस कद-काठी |
| पोशाक | बिना रंगी सूती छोटी कुर्ती, लपेटे हुए भांग के पायजामे, जूट की रस्सी का कमरबंद | हरा-नीला बिना बाँह का सदरी, नील-रंग घुटने तक का लपेट, केसरिया गले का कपड़ा |
| सिर | फीकी मजीठ-रंग की बँधी पट्टी | कसकर बँधे बाल, पीछे नीचा जूड़ा, बैंगनी डोरी |
| काम का सामान | कान के पीछे सरकंडे की क़लम | कमर पर डोरी से लटकी नामों की सूची |
| पैर | नंगे, पिंडलियों पर सूखी गाद | नंगे, पिंडलियों पर सूखी गाद |

| File | Use |
| --- | --- |
| [Sailor_Assistants.blend](Sailor_Assistants.blend) | Two scenes (`SailorA`, `SailorB`), one collection each: `CH_SailorA`, `CH_SailorB` |
| [CH_SailorA.fbx](CH_SailorA.fbx), [CH_SailorB.fbx](CH_SailorB.fbx) | Neutral skinned models with mouth shape keys |
| [Lineup](Sailor_Assistants_Lineup.png) | Side-by-side neutral comparison |
| [A portrait](SailorA_Portrait.png), [B portrait](SailorB_Portrait.png) | Relaxed-pose review renders |

## Known limits

- Supporting-cast level, like the citizen witnesses: simple lofts, no strand grooms, textile maps or cloth motion.
- The name list and reed pen are rigid props skinned to the hips and head. There is no writing hand pose yet. Add one before the logging shots.
- The sleeves and vest caps are shared from `citizen_witnesses.sleeves`. Check the shoulder joins before close-ups.

## Rebuild

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../../AGENTS.md)).

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_sailor_assistants.py
```
