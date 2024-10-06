from random import random, shuffle, choice
from geopy.distance import geodesic

import mysql.connector

# 数据库连接设置
connection = mysql.connector.connect(
    host='localhost',
    port=3306,
    database='vaccine_game',
    user='hechun',
    password='pass',
    charset='utf8mb4',
    collation='utf8mb4_unicode_ci'
)

# 定义必需的元素
REQUIRED_ELEMENTS = {'A', 'B', 'C', 'D'}

def get_airports():
    sql = '''SELECT iso_country, ident, name, type, latitude_deg, longitude_deg 
    FROM airport 
    WHERE continent = 'EU' 
    ORDER BY RAND() 
    LIMIT 16;'''
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql)
    result = cursor.fetchall()
    cursor.close()
    return result

# 根据ID获取元素名称
def get_element_name_by_id(element_id):
    sql = "SELECT name FROM element WHERE id = %s;"
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, (element_id,))
    result = cursor.fetchone()
    cursor.close()
    return result['name'] if result else None

def create_game(start_money, p_range, cur_airport, p_name, a_ports):
    cursor = connection.cursor(dictionary=True)
    # 插入新游戏记录
    sql = "INSERT INTO game (money, player_range, location, screen_name) VALUES (%s, %s, %s, %s);"
    cursor.execute(sql, (start_money, p_range, cur_airport, p_name))
    g_id = cursor.lastrowid

    # 获取所有元素及其数量
    sql = "SELECT id, name, total_quantity FROM element;"
    cursor.execute(sql)
    elements = cursor.fetchall()

    # 根据元素数量创建元素列表
    element_list = []
    for elem in elements:
        element_list.extend([elem['id']] * elem['total_quantity'])  # 使用元素ID

    # 打乱元素顺序
    shuffle(element_list)

    # 分配元素到不同机场
    assigned_airports = set()
    # 确保起始机场不被分配元素
    assigned_airports.add(cur_airport)
    for elem_id in element_list:
        # 筛选未被分配的机场
        available_ports = [port for port in a_ports if port['ident'] not in assigned_airports]
        if not available_ports:
            raise Exception("Not enough unique airports to assign all elements.")
        selected_port = choice(available_ports)
        assigned_airports.add(selected_port['ident'])
        # 插入到port_contents
        element_name = get_element_name_by_id(elem_id)
        sql = "INSERT INTO port_contents (game_id, airport, content_type, content_value) VALUES (%s, %s, %s, %s);"
        cursor.execute(sql, (g_id, selected_port['ident'], 'element', element_name))

    # 分配3个幸运箱到不同机场
    for _ in range(3):
        # 筛选未被分配的机场
        available_ports = [port for port in a_ports if port['ident'] not in assigned_airports]
        if not available_ports:
            raise Exception("Not enough unique airports to assign all lucky boxes.")
        selected_port = choice(available_ports)
        assigned_airports.add(selected_port['ident'])
        # 插入到port_contents
        sql = "INSERT INTO port_contents (game_id, airport, content_type) VALUES (%s, %s, %s);"
        cursor.execute(sql, (g_id, selected_port['ident'], 'lucky_box'))

    connection.commit()
    cursor.close()
    return g_id

# 获取机场信息
def get_airport_info(icao):
    sql = '''SELECT iso_country, ident, name, latitude_deg, longitude_deg
             FROM airport
             WHERE ident = %s'''
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, (icao,))
    result = cursor.fetchone()
    cursor.close()
    return result

# 检查当前机场的内容
def check_port_contents(g_id, cur_airport):
    sql = """SELECT id, content_type, content_value, found 
             FROM port_contents 
             WHERE game_id = %s AND airport = %s;"""
    cursor = connection.cursor(dictionary=True)
    cursor.execute(sql, (g_id, cur_airport))
    result = cursor.fetchall()
    cursor.close()
    return result

# 计算两个机场之间的距离
def calculate_distance(current, target):
    start = get_airport_info(current)
    end = get_airport_info(target)
    return geodesic(
        (start['latitude_deg'], start['longitude_deg']),
        (end['latitude_deg'], end['longitude_deg'])
    ).km

# 获取范围内的机场
def airports_in_range(icao, a_ports, p_range):
    in_range = []
    for a_port in a_ports:
        dist = calculate_distance(icao, a_port['ident'])
        if dist <= p_range and dist != 0:
            in_range.append(a_port)
    return in_range

# 更新位置和玩家状态
def update_location(icao, p_range, u_money, g_id):
    sql = '''UPDATE game SET location = %s, player_range = %s, money = %s WHERE id = %s'''
    cursor = connection.cursor()
    cursor.execute(sql, (icao, p_range, u_money, g_id))
    connection.commit()
    cursor.close()

# 标记内容为已找到
def mark_content_found(content_id):
    sql = "UPDATE port_contents SET found = 1 WHERE id = %s;"
    cursor = connection.cursor()
    cursor.execute(sql, (content_id,))
    connection.commit()
    cursor.close()

# 购买额外范围
def buy_extra_range(player_range, money):
    while True:
        # 询问玩家想购买多少范围
        range_to_buy = input("How much range do you want to buy? (in km, multiples of 100): ").strip()

        # 验证输入
        try:
            range_to_buy = int(range_to_buy)
            if range_to_buy <= 0 or range_to_buy % 100 != 0:
                print("Please enter a valid amount (must be a positive multiple of 100).")
                continue
        except ValueError:
            print("Invalid input. Please enter a number.")
            continue

        # 计算费用
        cost = (range_to_buy // 100) * 100

        # 检查玩家是否有足够的钱
        if cost > money:
            print(f"You don't have enough money. You need ${cost} but only have ${money}.")
            continue

        # 扣除费用并更新范围
        money -= cost
        player_range += range_to_buy
        print(f"You bought an extra {range_to_buy}km of range.")
        print(f"New range: {player_range}km, Remaining money: ${money}")
        break  # 成功购买后退出循环

    return player_range, money

# 游戏开始
def main():
    # 询问是否显示故事背景
    storyDialog = input('Do you want to read the background story? (Y/N): ')
    if storyDialog.upper() == 'Y':
        print("Your mission is to fly to different airports to collect essential elements (A, B, C, D) needed to create a vaccine.")
        print("Each element has a limited number available in the game.")
        print("A random airport will also contain a lucky box, which costs $100 to open.")
        print("The lucky box may contain an additional element or be empty.")
        print("If you collect all required elements within the budget provided at the start of the game, you win!")

    # 游戏设置
    input('Press enter to start! ')
    player = input('Type player name: ')
    game_over = False
    win = False

    # 初始资金和范围
    money = 1000
    player_range = 6000

    # 已收集的元素
    collected_elements = set()

    # 获取所有机场
    all_airports = get_airports()
    # 起始机场的ICAO
    start_airport = all_airports[0]['ident']

    # 当前机场
    current_airport = start_airport

    # 创建游戏并分配内容
    try:
        game_id = create_game(money, player_range, start_airport, player, all_airports)
    except Exception as e:
        print(f"Error creating game: {e}")
        connection.close()
        exit()

    # 游戏循环
    while not game_over:
        # 获取当前机场信息
        airport = get_airport_info(current_airport)
        print(f"\nYou are at {airport['name']} (ICAO: {airport['ident']}). Base airport: {start_airport}")
        print(f"You have ${money:.0f} and {player_range:.0f}km of range.")
        print(f"Collected elements: {', '.join(collected_elements) if collected_elements else 'None'}")

        # 购买额外范围的选项
        buy_range = input('Do you want to buy extra range? (Y/N): ').strip().upper()
        if buy_range == 'Y':
            if money < 100:  # 检查玩家是否有钱购买任何范围
                print("\033[33mYou don't have enough money to buy extra range.\033[0m")
            else:
                player_range, money = buy_extra_range(player_range, money)

        # 暂停
        input("\033[32mPress Enter to continue...\033[0m")

        # 显示范围内的机场
        airports = airports_in_range(current_airport, all_airports, player_range)
        print(f"\033[34mThere are {len(airports)} airports in range:\033[0m")
        if len(airports) == 0:
            print('\033[33mYou are out of range.\033[0m')
            game_over = True
            break  # 如果范围内没有机场，结束游戏
        else:
            print("Airports:")
            for airport_info in airports:
                ap_distance = calculate_distance(current_airport, airport_info['ident'])
                print(f"{airport_info['name']}, ICAO: {airport_info['ident']}, Distance: {ap_distance:.0f}km")

        # 询问目的地
        dest = input('Enter destination ICAO: ').strip().upper()
        # 验证目的地
        dest_airports = [airport_info['ident'] for airport_info in airports]
        if dest not in dest_airports:
            print("\033[31mInvalid destination. Please choose an airport within range.\033[0m")
            continue

        # 计算飞行距离
        selected_distance = calculate_distance(current_airport, dest)
        if selected_distance > player_range:
            print("\033[31mYou don't have enough range to fly to this destination.\033[0m")
            continue

        # 更新范围和位置
        player_range -= selected_distance
        update_location(dest, player_range, money, game_id)
        current_airport = dest
        if player_range < 0:
            game_over = True

        # 检查新机场的内容
        contents = check_port_contents(game_id, current_airport)
        for content in contents:
            if content['found'] == 0:
                if content['content_type'] == 'element':
                    element = content['content_value']
                    if element not in collected_elements:
                        collected_elements.add(element)
                        print(f"\033[32mYou found Element {element} at {airport['name']}!\033[0m")
                        mark_content_found(content['id'])

                        # 检查是否赢得游戏
                        if REQUIRED_ELEMENTS.issubset(collected_elements):
                            win = True
                            game_over = True
                            print("\033[32mContratulations!You have collected all required elements!\033[0m")
                            break
                    else:
                        print(f"\033[33mYou already have Element {element}.\033[0m")

                elif content['content_type'] == 'lucky_box':
                    question = input('Do you want to open the lucky box by $100? (Y/N): ').strip().upper()
                    if question == 'Y':
                        if money >= 100:
                            money -= 100
                            lucky_box_result = choice(['A', 'B', 'C', 'D', 'Empty'])
                            if lucky_box_result in REQUIRED_ELEMENTS:
                                if lucky_box_result not in collected_elements:
                                    collected_elements.add(lucky_box_result)
                                    print(f"\033[32mCongratulations! You found Element {lucky_box_result} in the lucky box.\033[0m")

                                    # 检查是否赢得游戏
                                    if REQUIRED_ELEMENTS.issubset(collected_elements):
                                        win = True
                                        game_over = True
                                        print("\033[32mContratulations!You have collected all required elements!\033[0m")
                                        break
                                else:
                                    print(f"\033[31mThe lucky box is empty. You already have Element {lucky_box_result}.\033[0m")
                            else:
                                print('\033[31mThe lucky box is empty.\033[0m')
                            mark_content_found(content['id'])
                        else:
                            print("\033[31mYou don't have enough money to open the lucky box.\033[0m")
            else:
                print("\033[31mSorry! It's an empty airport!\033[0m")

    # 游戏结束
    print(f"\n\033[31m{'You won!' if win else 'You lost!'}\033[0m")
    if win:
        print(f"Congratulations! You collected all required elements: {', '.join(collected_elements)}.")
    else:
        print(f"You have ${money:.0f} left and {player_range:.0f}km of range remaining.")

    # 显示已收集的元素
    if collected_elements:
        print(f"You collected the following elements: {', '.join(collected_elements)}.")
    else:
        print("You didn't collect any elements.")

    # 关闭数据库连接
    connection.close()

if __name__ == "__main__":
    main()
