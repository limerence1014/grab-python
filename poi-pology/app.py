#! /usr/local/bin/python3
# coding: utf-8
# __author__ = "Liu jiao"
# __date__ = 2019/10/16 16:11


from urllib.parse import quote
import json
import os
from transCoordinateSystem import gcj02_to_wgs84, gcj02_to_bd09
import area_boundary as  area_boundary
import city_grid as city_grid
import time
import collections
import pandas as pd
from requests.adapters import HTTPAdapter
import requests

#from shp import trans_point_to_shp


'''
版本更新说明：
2020.06.19:
    1.清除了poi数据写入shp文件相关操作

'''

#################################################需要修改###########################################################

## TODO 1.划分的网格距离，0.02-0.05最佳，建议如果是数量比较多的用0.01或0.02，如餐厅，企业。数据量少的用0.05或者更大，如大学
pology_split_distance = 0.02

## TODO 2. 城市编码，参见高德城市编码表，注意需要用adcode列的编码
city_code = '320000'

## TODO 3. POI类型编码，类型名或者编码都行，具体参见《高德地图POI分类编码表.xlsx》
typs = ['住宅区']  # ['企业', '公园', '广场', '风景名胜', '小学']

## TODO 4. 高德开放平台密钥
gaode_key = [
	 'e66456c0d1ae5ed489675e977aef9b3d',
	 'f86467a2f7e77095053ede14ced61787',
]

# TODO 5.输出数据坐标系,1为高德GCJ20坐标系，2WGS84坐标系，3百度BD09坐标系
coord = 1

############################################以下不需要动#######################################################################


poi_pology_search_url = 'https://restapi.amap.com/v3/place/polygon'

buffer_keys = collections.deque(maxlen=len(gaode_key))


def init_queen():
    for i in range(len(gaode_key)):
        buffer_keys.append(gaode_key[i])
    print('当前可供使用的高德密钥：', buffer_keys)


# 根据城市名称和分类关键字获取poi数据
def getpois(grids, keywords):
    if buffer_keys.maxlen == 0:
        print('密钥已经用尽，程序退出！！！！！！！！！！！！！！！')
        exit(0)
    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥

    i = 1
    poilist = []
    while True:  # 使用while循环不断分页获取数据
        result = getpoi_page(grids, keywords, i, amap_key)
        print("当前爬取结果:", result)
        if result != None:
            result = json.loads(result)  # 将字符串转换为json
            try:
                if result['count'] == '0':
                    break
            except Exception as e:
                print('出现异常：', e)

            if result['infocode'] == '10001' or result['infocode'] == '10003' or result['infocode'] == '10044' or result['infocode'] == '30001':
                print(result)
                print('无效的密钥！！！！！！！！！！！！！，重新切换密钥进行爬取')
                buffer_keys.remove(buffer_keys[0])
                try:
                    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥
                except Exception as e:
                    print('密钥已经用尽，程序退出...')
                    exit(0)
                result = getpoi_page(grids, keywords, i, amap_key)
                result = json.loads(result)
            hand(poilist, result)
        i = i + 1
    return poilist


# 数据写入csv文件中
def write_to_csv(poilist, citycode, classfield, coord):
    data_csv = {}
    lons, lats, names, addresss, pcodes, pnames, pcitycodes, citynames, adcodes, adnames, parents, business_areas, types, typecodes, ids, type_1s, type_2s, type_3s, type_4s = [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], [], []

    if len(poilist) == 0:
        print("处理完成，当前citycode:" + str(citycode), ", classfield为：", str(classfield) + "，数据为空，，，结束.......")
        return None, None

    for i in range(len(poilist)):
        location = poilist[i].get('location')
        name = poilist[i].get('name')
        address = poilist[i].get('address')
        parent = poilist[i].get('parent')
        pcode = poilist[i].get('pcode')
        pname = poilist[i].get('pname')
        pcitycode = poilist[i].get('citycode')
        cityname = poilist[i].get('cityname')
        adcode = poilist[i].get('adcode')
        adname = poilist[i].get('adname')
        business_area = poilist[i].get('business_area')
        type = poilist[i].get('type')
        typecode = poilist[i].get('typecode')
        lng = str(location).split(",")[0]
        lat = str(location).split(",")[1]
        id = poilist[i].get('id')

        if (coord == 2):
            result = gcj02_to_wgs84(float(lng), float(lat))
            lng = result[0]
            lat = result[1]
        if (coord == 3):
            result = gcj02_to_bd09(float(lng), float(lat))
            lng = result[0]
            lat = result[1]
        type_1, type_2, type_3, type_4 = '','','',''
        if str(type) != None and str(type) != '':
            type_strs = type.split(';')
            for i in range(len(type_strs)):
                ty = type_strs[i]
                if i == 0:
                    type_1 = ty
                elif i == 1:
                    type_2 = ty
                elif i == 2:
                    type_3 = ty
                elif i == 3:
                    type_4 = ty

        lons.append(lng)
        lats.append(lat)
        names.append(name)
        parents.append(parent)
        addresss.append(address)
        pcodes.append(pcode)
        pnames.append(pname)
        pcitycodes.append(pcitycode)
        citynames.append(cityname)
        adcodes.append(adcode)
        adnames.append(adname)
        if business_area == []:
            business_area = ''
        business_areas.append(business_area)
        types.append(type)
        typecodes.append(typecode)
        ids.append(id)
        type_1s.append(type_1)
        type_2s.append(type_2)
        type_3s.append(type_3)
        type_4s.append(type_4)
    data_csv['lon'], data_csv['lat'], data_csv['name'], data_csv['parent'], data_csv['address'], data_csv['pcode'], data_csv['pname'], \
    data_csv['citycode'], data_csv['cityname'], data_csv['adcode'], data_csv['adname'], data_csv['business_area'], data_csv['type'], data_csv['typecode'], data_csv['id'], data_csv[
        'type1'], data_csv['type2'], data_csv['type3'], data_csv['type4'] = \
        lons, lats, names, parents, addresss, pcodes, pnames, pcitycodes, citynames, adcodes, adnames, business_areas, types, typecodes, ids, type_1s, type_2s, type_3s, type_4s

    df = pd.DataFrame(data_csv)

    folder_name = 'poi-' + citycode + "-" + classfield
    folder_name_full = 'data' + os.sep + folder_name + os.sep
    if os.path.exists(folder_name_full) is False:
        os.makedirs(folder_name_full)
    file_name = 'poi-' + citycode + "-" + classfield + ".csv"
    file_path = folder_name_full + file_name
    df.to_csv(file_path, index=False, encoding='utf_8_sig')


    # 20210528 新转存一个全量的json 用于后面使用
    data_all_csv = {}
    all_ids, all_datas = [],[]
    for i in range(len(poilist)):
        all_id = poilist[i].get('id')
        all_data = poilist[i]
        all_ids.append(all_id)
        all_datas.append(all_data)

    data_all_csv['source_id'], data_all_csv['source_data'] = all_ids, all_datas
    allDf = pd.DataFrame(data_all_csv)
    all_file_name = 'poi-all-source-' + citycode + "-" + classfield + ".csv"
    all_file_path = folder_name_full + all_file_name
    allDf.to_csv(all_file_path, index=False, encoding='utf_8_sig')
    #转存完毕


    print('写入成功')
    return folder_name_full, file_name


# 将返回的poi数据装入集合返回
def hand(poilist, result):
    # result = json.loads(result)  # 将字符串转换为json
    pois = result['pois']
    for i in range(len(pois)):
        poilist.append(pois[i])


# 单页获取pois
def getpoi_page(grids, types, page, key):
    polygon = str(grids[0]) + "," + str(grids[1]) + "|" + str(grids[2]) + "," + str(grids[3])
    req_url = poi_pology_search_url + "?key=" + key + '&extensions=all&types=' + quote(
        types) + '&polygon=' + polygon + '&offset=25' + '&page=' + str(
        page) + '&output=json'
    print('请求url：', req_url)

    s = requests.Session()
    s.mount('http://', HTTPAdapter(max_retries=5))
    s.mount('https://', HTTPAdapter(max_retries=5))
    try:
        data = s.get(req_url, timeout=5)
        return data.text
    except requests.exceptions.RequestException as e:
        data = s.get(req_url, timeout=5)
        return data.text
    return None


def get_drids(min_lng, max_lat, max_lng, min_lat, keyword, key, pology_split_distance, all_grids):
    grids_lib = city_grid.generate_grids(min_lng, max_lat, max_lng, min_lat, pology_split_distance)

    print('划分后的网格数：', len(grids_lib))
    print(grids_lib)

    # 3. 根据生成的网格爬取数据，验证网格大小是否合适，如果不合适的话，需要继续切分网格
    for grid in grids_lib:
        one_pology_data = getpoi_page(grid, keyword, 1, key)
        data = json.loads(one_pology_data)
        print(data)

        while int(data['count']) > 890:
            get_drids(grid[0], grid[1], grid[2], grid[3], keyword, key, pology_split_distance / 2, all_grids)


        all_grids.append(grid)
    return all_grids


def get_data(city, keyword, coord):
    # 1. 获取城市边界的最大、最小经纬度
    amap_key = buffer_keys[0]  # 总是获取队列中的第一个密钥
    max_lng, min_lng, max_lat, min_lat = area_boundary.getlnglat(city, amap_key)

    print('当前城市：', city, "max_lng, min_lng, max_lat, min_lat：", max_lng, min_lng, max_lat, min_lat)

    # 2. 生成网格切片格式：

    grids_lib = city_grid.generate_grids(min_lng, max_lat, max_lng, min_lat, pology_split_distance)
    # grids_lib = [[116.462723, 31.784513, 116.482723, 31.764513]]
    print('划分后的网格数：', len(grids_lib))
    print(grids_lib)

    all_data = []
    begin_time = time.time()

    print('==========================正式开始爬取啦！！！！！！！！！！！================================')

    for grid in grids_lib:
        # grid格式：[112.23, 23.23, 112.24, 23.22]
        one_pology_data = getpois(grid, keyword)

        print('===================================当前矩形范围：', grid, '总共：',
              str(len(one_pology_data)) + "条数据.............................")

        all_data.extend(one_pology_data)

    end_time = time.time()
    print('全部：', str(len(grids_lib)) + '个矩形范围', '总的', str(len(all_data)), '条数据, 耗时：', str(end_time - begin_time),
          '正在写入CSV文件中')
    file_folder, file_name = write_to_csv(all_data, city, keyword, coord)
    # 写入shp
    #if file_folder is not None:
        #trans_point_to_shp(file_folder, file_name, 0, 1, pology_split_distance, keyword)


if __name__ == '__main__':
    # 初始化密钥队列
    init_queen()

    for type in typs:
        get_data(city_code, type, coord)
