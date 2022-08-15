#######################################
# src = 'Wesee_sample_parsed'
src_pt = 'weseel_RAplus1.pt'
target = 'weseel_RAplus1-Dobo_sample_parsed'

cb = src_pt[:src_pt.find(".")]
cb_dir = '../../dataset/'+cb+'-'+target

conf_def = 0.7 #보다 높아야 유효
conf = {  # conf 개별 설정
    "Zebra_Cross":0.8,
    "R_Signal":0.6,
    "G_Signal":0.6,
    # "Braille_Block":0.7,
    # "person":,
    # "dog":,
    # "tree":,
    # "car":,
    # "bus":,
    # "truck":,
    # "motorcycle":,
    # "bicycle":,
    # "train":,
    # "wheelchair":,
    # "stroller":,
    # "kickboard":,
    # "bollard":,
    # "manhole":,
    # "labacon":,
    # "bench":,
    # "barricade":,
    # "pot":,
    # "table":,
    # "chair":,
    # "fire_hydrant":,
    # "movable_signage":,
    # "bus_stop":
}
iou = 0.2 #보다 높고 클래스가 같으면 무시
iou_warning = 0.4 #보다 높으면 사용자 직접확인

img_size= [640, 360]
#######################################
import yaml, os, shutil, json
from PIL import Image, ImageDraw, ImageFont
import torch
from models.common import AutoShape, DetectMultiBackend
global final, ignore, added
final=[]  # 통합클래스이름
class_book={}
ignore=[]  # src 중 무시할 클래스이름
img_box=[0,0,0,0] # Number of total [images, bboxes, tiny, large]
added={}

# src_dir = '../../dataset/'+src
target_dir = '../../dataset/'+target
font = ImageFont.truetype("utils/arial_bold.ttf", 15)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"using devide {DEVICE}")


model = AutoShape( 
    DetectMultiBackend(weights=src_pt, device=torch.device(DEVICE))
)

def IoU(box1, box2):
    # box = (x1, y1, x2, y2)
    box1_area = (box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1)
    box2_area = (box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1)

    # obtain x1, y1, x2, y2 of the intersection
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    # compute the width and height of the intersection
    w = max(0, x2 - x1 + 1)
    h = max(0, y2 - y1 + 1)

    inter = w * h
    iou = inter / (box1_area + box2_area - inter)
    return iou

def draw_box(feature, coor, text, color):
    feature.line((coor[0], coor[1], coor[0], coor[3]), fill=color, width=2)
    feature.line((coor[0], coor[3], coor[2], coor[3]), fill=color, width=2)
    feature.line((coor[2], coor[3], coor[2], coor[1]), fill=color, width=2)
    feature.line((coor[2], coor[1], coor[0], coor[1]), fill=color, width=2)
    bbox = font.getbbox(text)
    text_shift = 12
    feature.rectangle((coor[0], coor[1]-text_shift, coor[0] + bbox[2], coor[1]), fill=color)
    feature.text((coor[0],coor[1]-text_shift), text, (255,255,255), font=font)

def cross_boxing():
    global final, ignore, img_box, cases

    for type in ['/train','/val','/test']:
        image_folder = target_dir+type+'/images/'
        label_folder = target_dir+type+'/labels/'
        if os.path.exists(image_folder):
            image_list = os.listdir(image_folder)
            for image_file in image_list:
                image = Image.open(image_folder+image_file)

                # YOLOv5 model
                result = model(image, size=640).pandas().xyxy[0].to_dict(orient="records")

                # print(result)
                # Format is as follows:
                # [{"xmin":57.0689697266,"ymin":391.7705993652,"xmax":241.3835449219,"ymax":905.7978515625,"confidence":0.8689641356,"class":0.0,"name":"person"},
                # {"xmin":667.6612548828,"ymin":399.3035888672,"xmax":810.0,"ymax":881.3966674805,"confidence":0.8518877029,"class":0.0,"name":"person"},
                # {"xmin":222.8783874512,"ymin":414.774230957,"xmax":343.804473877,"ymax":857.8250732422,"confidence":0.8383761048,"class":0.0,"name":"person"},
                # {"xmin":4.2053861618,"ymin":234.4476776123,"xmax":803.7391357422,"ymax":750.0233764648,"confidence":0.6580058336,"class":5.0,"name":"bus"},
                # {"xmin":0.0,"ymin":550.5960083008,"xmax":76.6811904907,"ymax":878.669921875,"confidence":0.4505961835,"class":0.0,"name":"person"}]

                gts = []
                original_txt = open(label_folder+image_file[:image_file.find("jpg")]+"txt", 'r')
                originals = original_txt.readlines()
                for line in originals:
                    tok = list(map(float,line.split()))
                    tok[0] = int(tok[0])
                    gts.append(tok)
                # Format is as follows:
                # [[23, 0.19799479166666664, 0.4273148148148148, 0.20296875, 0.11388888888888889],
                # [23, 0.038734375, 0.4248796296296296, 0.07642708333333334, 0.11018518518518519],
                # [23, 0.39765364583333335, 0.43243518518518514, 0.07333854166666663, 0.07290740740740737]]
                
                for bbox in result:
                    is_addbox=False
                    name = bbox['name']
                    if(name in ignore):
                       continue 
                    if(name in conf.keys() and bbox['confidence'] > conf[name]) or (name not in conf.keys() and bbox['confidence'] > conf_def):
                        is_addbox = True
                        for gt in gts:
                            predict_box = [bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]]
                            xc = gt[1]*img_size[0]
                            yc = gt[2]*img_size[1]
                            w = gt[3]*img_size[0]
                            h = gt[4]*img_size[1]
                            gt_box = [xc-w/2, yc-h/2, xc+w/2, yc+h/2]
                            this_iou = IoU(predict_box, gt_box)

                            # Manual Labeling
                            if(this_iou > iou_warning):
                                if(bbox['class']==gt[0]) and (name!="tree"):
                                    is_addbox = False
                                    print(f"High IoU Bbox overlap ignored : {name} on GT {final[gt[0]]}")
                                    break
                                draw = ImageDraw.Draw(image)
                                draw_box(draw, gt_box, final[int(gt[0])],'red')
                                draw_box(draw, predict_box, name,'yellow')
                                image.show()
                                ans = input("Confirm new box(yellow)?: [y,n]")
                                if ans!='y':
                                    is_addbox = False
                                    print(f"Manually Bbox overlap ignored : {name} on GT {final[gt[0]]}")
                                    break

                            # High IoU
                            elif(this_iou > iou):
                                if(bbox['class']==gt[0]) and (name!="tree"):
                                    is_addbox = False
                                    print(f"Bbox overlap ignored : {name} on GT {final[gt[0]]}")
                                    break
                                print(f"Bbox overlapped new: {name} on GT: {final[gt[0]]}")
                            

                        if is_addbox:
                            if(name=="tree"):  # Special case
                                print("WARNING :: Tree conflict case is not deployed yet...")
                            else:  # Normal case
                                # print(f"Normally adding new box: {name}")
                                xc = (bbox["xmax"]+bbox["xmin"])/2/img_size[0]
                                yc = (bbox["ymax"]+bbox["ymin"])/2/img_size[1]
                                w = (bbox["xmax"]-bbox["xmin"])/img_size[0]
                                h = (bbox["ymax"]-bbox["ymin"])/img_size[1]
                                new_box=[bbox['class'], xc, yc, w, h]
                                gts.append(new_box)
                                if cases[name]=='Invalid':
                                    cases[name]=1
                                else:
                                    cases[name]+=1
                                if not name in added.keys():
                                    added[name]=1
                                else:
                                    added[name]+=1
                                img_box[1]+=1
                                    
                with open(cb_dir+type+'/labels/'+image_file[:image_file.find(".")]+'.txt','w') as t:
                    for nodes in gts:
                        for node in nodes:
                            t.write(str(node)+' ')
                        t.write('\n')


# def yaml_dumper():
#     content={}
#     with open(cb_dir+'/'+'data.yaml','w') as y:
#          yaml.dump(content, y)

def autolabel_yaml_writer():
    global origin_data_stat, img_box
    o = origin_data_stat
    train_val_test = o['Train-Val-Test']
    add_info[src_pt] = added

    nc = len(final)
    with open(cb_dir+"/data.yaml", 'w') as f:
        f.write("path: "+cb_dir+"\ntrain: train/images\nval: val/images\n")
        f.write("test: test/images\n\nnc: %d\nnames: ["%nc)
        
        for i in range(nc):
            f.write(f"{final[i]}")
            if(i<nc-1):
                f.write(', ')
            else:
                f.write(']')
        f.write("\n# Dataset statistics: \nTotal imgs: %d\nTrain-Val-Test: [%d,%d,%d]\n\n"%(img_box[0],
            train_val_test[0],train_val_test[1],train_val_test[2]))
        f.write("Too small boxes ignored: %d\nToo large boxes ignored: %d\n\n"%(img_box[2],img_box[3]))
        f.write("Total Bbox: %d\nBbox distribution:\n"%(img_box[1]))
        for i in range(nc):
            f.write("    %s: %s\n"%(final[i],cases[final[i]]))
        f.write("\nAuto labels:  # 순서는 라벨링 된 순서와 상관없음\n")
        for pt in add_info.keys():
            f.write(f"    {pt}: {added}\n")
        f.close()

def data_init():
    global final, ignore, origin_data_stat, cases, img_box, add_info
    add_info={}

    if("wesee" in src_pt.lower()):
        data_name = 'Wesee'
    elif("dobo" in src_pt.lower()):
        data_name = 'Dobo'
    elif("chair" in src_pt.lower()):
        data_name = 'Chair'
    elif("coco" in src_pt.lower()):
        data_name = 'Coco'
    else:
        print("Dataset type auto detect failed. Exiting...")
        exit()
    # src_yaml = yaml.safe_load(open(src_dir +'/data_old.yaml', encoding='UTF-8'))
    class_json = json.load(open('../class.json'))
    final = class_json['Final']['Original']
    ignore = class_json[data_name]['Ignore']
    class_book = class_json['Final']['Label']
    origin_data_stat = yaml.safe_load(open(target_dir+'/data.yaml', encoding='UTF-8'))
    img_box[0] = origin_data_stat['Total imgs']
    img_box[1] = origin_data_stat['Total Bbox']
    img_box[2] = origin_data_stat['Too small boxes ignored']
    img_box[3] = origin_data_stat['Too large boxes ignored']
    cases = origin_data_stat['Bbox distribution']
    if 'Auto labels' in origin_data_stat.keys():
        add_info = origin_data_stat['Auto labels']

def main():
    if not os.path.exists(cb_dir):
        print("Copying images from src folder...")
        for dir in ['','/train','/val','/test']:
            os.mkdir(cb_dir+dir)
        for dir in ['/train/images','/val/images','/test/images']:
            if os.path.exists(target_dir+dir):
                shutil.copytree(target_dir+dir, cb_dir+dir)
    
    assigned=False
    for dir in ['/train/labels','/val/labels','/test/labels']:
        if os.path.exists(cb_dir+dir):
            if not assigned:
                ans = input("기존 오토라벨을 지우고 계속합니다. [y,n] : ")
                if(ans!='y'):
                    exit() 
                else:
                    assigned=True
            shutil.rmtree(cb_dir+dir)
        if os.path.exists(target_dir+dir):
            os.mkdir(cb_dir+dir)
    data_init()
    cross_boxing()
    # yaml_dumper()
    autolabel_yaml_writer()
    print(f"Following bboxes are added: {added}")


if __name__ == "__main__":
    main()