# गवाह: दो अन्य नगरवासी

कहानी इन दोनों का पेशा, लिंग या आपसी रिश्ता तय नहीं करती, इसलिए मॉडल भी कुछ तय नहीं करते। दोनों एक ही नागरिक रिग (34 हड्डियाँ, वही चेहरा और मुँह के phoneme shapes) पर बने हैं। फ़र्क़ सिर्फ़ रूपरेखा और पोशाक का है।

| | नगरवासी A (`CitizenA`) | नगरवासी B (`CitizenB`) |
| --- | --- | --- |
| क़द | लगभग 1.79 m, लंबा और दुबला | लगभग 1.63 m, ठोस कद-काठी |
| चेहरा | संकरा | चौड़ा |
| पोशाक | लंबा नील-रंग अंगरखा, रेतिया पायजामा, जंग-रंग कमरपट्टी, सैंडल | छोटा गेरुआ कुर्ता, कोयले-रंग ढीला पायजामा, काई-हरा कंधे का शॉल, कपड़े के जूते |
| सिर | जंग-रंग की लिपटी पगड़ी | कसकर बँधे बाल, पीछे नीचा जूड़ा |

| File | Use |
| --- | --- |
| [Citizen_Witnesses.blend](Citizen_Witnesses.blend) | Two scenes (`CitizenA`, `CitizenB`), one collection each: `CH_CitizenA`, `CH_CitizenB` |
| [CH_CitizenA.fbx](CH_CitizenA.fbx), [CH_CitizenB.fbx](CH_CitizenB.fbx) | Neutral skinned models with mouth shape keys |
| [Lineup](Citizen_Witnesses_Lineup.png) | Side-by-side neutral comparison |
| [A portrait](CitizenA_Portrait.png), [B portrait](CitizenB_Portrait.png) | Relaxed-pose review renders |

## Known limits

- This is a first pass at the supporting-cast level, not the hero level of Vikram. The costumes are simple lofts. There are no strand grooms, textile maps or cloth motion.
- Skin shows through at the shoulders and knees of A, where garment layers meet the arm and leg meshes. Fix this before close-ups.
- The B shawl and A turban tail are rigid and skinned to the chest and head.

## Rebuild

Replace `blender` with `D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe` (see [AGENTS.md](../../../AGENTS.md)).

```powershell
blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_citizen_witnesses.py
```
