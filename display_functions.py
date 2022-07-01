from prettytable import PrettyTable
from PIL import Image, ImageDraw, ImageFont


def sortListBy(stat_list, sort_column):
    sortedL = []

    for d in stat_list:
        for f in range(len(sortedL)):
            lPDR = float(stat_list[d][sort_column])
            sPDR = sortedL[f][1]

            if lPDR > sPDR:
                sortedL.insert(f, (d, lPDR))
                break
        else:
            sortedL.append((d, float(stat_list[d][sort_column])))

    return sortedL


def renderStatsImage(text_data):

    def getSize(txt, font):
        testImg = Image.new('RGB', (1, 1))
        testDraw = ImageDraw.Draw(testImg)
        return testDraw.textsize(txt, font)

    fontname = "UbuntuMono-R.ttf"
    fontsize = 14
    text = text_data

    colorText = 'black'
    colorOutline = 'red'
    colorBg = 'white'

    font = ImageFont.truetype(fontname, fontsize)
    width, height = getSize(text, font)
    img = Image.new('RGB', (width + 4, height + 4), colorBg)
    d = ImageDraw.Draw(img)
    d.text((2, 0), text, fill=colorText, font=font)
    d.rectangle((0, 0, width + 3, height + 3), outline=colorOutline)

    img.save('test.png')
    return


def createPrettyTable(sorted_list, pretty_table_obj, stat_dict):

    for i in sorted_list:
        team = i[0]
        tstats = stat_dict[team]
        temprow = []
        for j in pretty_table_obj.field_names:
            if j == 'Team':
                temprow.append(team)
            elif j == 'Player':
                temprow.append(team)
            else:
                temprow.append(tstats[j])
        pretty_table_obj.add_row(temprow)

    return pretty_table_obj
