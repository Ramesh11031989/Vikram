# अध्याय १ — दृष्टि की जाँच

महल की खिड़की, घाट, गोपाल की नाव, अनाज मंडी और हलवाई की छत एक ही मीटर-स्केल Blender scene में हैं। [E01_Ghat_Sightlines.blend](E01_Ghat_Sightlines.blend)

## तीन कैमरे और पाँच रेंडर

| Frame | कैमरा | इस फ़्रेम में देखें |
| ---: | --- | --- |
| 1 | महल की खिड़की | [सुबह, पानी −2.20 m और पाँच सूखी सीढ़ियाँ](E01_Sightline_001.png) |
| 49 | वही खिड़की, वही कैमरा और लेंस | [बाद में, पानी −1.40 m और तीन सूखी सीढ़ियाँ](E01_Sightline_049.png) |
| 97 | हलवाई की छत से आँख की ऊँचाई | [घाट दिखता है, मंडी का छप्पर फाटक ढकता है](E01_Sightline_097.png) |
| 145 | नाव में बैठे गोपाल की आँख की ऊँचाई | [दीया, तिरछी पीठ और लाल कंधे का कपड़ा](E01_Sightline_145.png) |
| 238 | वही कैमरा, नाव घूम चुकी है | [नाव की नज़र चौकी से हटकर आगे नदी की ओर](E01_Sightline_238.png) |

Blender की Timeline पर इन्हीं फ़्रेमों पर कैमरे बँधे हैं। घाट के आठ पायदानों पर कैमरे से छोड़ी गई किरणें गिनती की पुष्टि करती हैं। हलवाई के कैमरे से घाट के चार नमूने दिखते हैं और फाटक के सभी बारह नमूनों पर मंडी का छप्पर पहला अवरोध है। गोपाल का कैमरा नाव के rig पर है। चौकी पर मौजूदा अनाम पात्र की पीठ और उसका कपड़ा दिखता है। दीये को पटिया के किनारे एक छोटे आधार पर रखा है, जहाँ से उसकी लौ दिखती है और कपड़े पर सीधे रोशनी पड़ती है। फाटक गवाही के समय नीचे है और बाद में उठता है। [14 जाँचों की रिपोर्ट](E01_Ghat_Sightlines_Check.json)

यह साझा सीन दृष्टि, जगह और रोशनी की जाँच के लिए है। गोपाल, भतीजी और चप्पू के बीच का अभिनय अलग performance pass में जोड़ा जाएगा।

## अध्याय के मॉडल और एसेट रेंडर

| Review sheet | इसमें क्या है |
| --- | --- |
| [मुख्य और प्रमुख सहायक किरदार](../Asset_Review/01_Lead_Cast_And_Acting.jpg) | चेहरे, पोशाक और अभिनय की मुद्राएँ |
| [गवाह और सहायक कास्ट](../Asset_Review/02_Witnesses_And_Support.jpg) | सात गवाहों की पहचान, बच्चे, नाविक, मुंशी, पहरेदार और भीड़ |
| [पाँच सेट और उनकी जगहें](../Asset_Review/03_Sets_And_Geography.jpg) | महल, घाट, बस्ती और मंडी, श्मशान और शरण-ढलान |
| [सबूत और कहानी के प्रॉप्स](../Asset_Review/04_Evidence_And_Story_Props.jpg) | काग़ज़, पोटली, घोड़ा, थैला, गाय और कटी रस्सी |

अलग से बड़े [सात बयान और सातवें पन्ने का मोड़](../Asset_Review/E01_Evidence_Statements.png), [पहुँच-सूची और आदेश](../Asset_Review/E01_Evidence_Decisions.png) और [पोटली की तीन अवस्थाएँ और बही](../Asset_Review/E01_Evidence_Bundle.png) देखें। शीटों में मौजूदा एसेट रेंडर और Git शाखाओं के रिव्यू भी शामिल हैं। मौसी के दृश्य अभी ब्लॉकआउट हैं। अंतिम राजादेश की कुछ लिखावट मुहर से टकराती है और क्लोज़-अप के लिए अलग टाइपसेटिंग चाहिए।

## Rebuild

The assembly appends editable collections from `Blender/Sets/SET_Palace.blend`, `SET_Ghat.blend` and `SET_Town.blend`, and the actor from `Blender/Characters/Anonymous_Red_Cloth/Anonymous_Red_Cloth.blend`. The Ghat source supplies the river, gate, stairs and moving boat. A trimmed portion of the palace terrain fills the distance. Open the assembled file directly to edit the copied assets and the three cameras.

```powershell
$blender = 'D:\Tools\Blender\blender-5.2.2-windows-x64\blender.exe'
$sightlines = 'Production/E01/Sightlines/E01_Ghat_Sightlines.blend'
& $blender --background --factory-startup --python-exit-code 1 --python Blender/tools/build_e01_ghat_sightlines.py
& $blender --background $sightlines --python-exit-code 1 --python Blender/tools/validate_e01_ghat_sightlines.py -- --output Production/E01/Sightlines/E01_Ghat_Sightlines_Check.json
& $blender --background $sightlines --render-output '//E01_Sightline_###' --render-frame '1,49,97,145,238'
```
