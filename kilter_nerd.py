import getopt
import glob
import os
import sys
import sqlite3

# Some needed packages
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mpl_tck
from scipy import sparse
from scipy.ndimage import gaussian_filter

# add alpha (transparency) to a colormap
import matplotlib.cm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.colors import ListedColormap
import seaborn as sns
import matplotlib.image as mpimg
import numpy.random as random
import re
import emojis
import pandas as pd

import json
from prettytable import PrettyTable

ROLE_START = 12
ROLE_HAND = 13
ROLE_FINISH = 14
ROLE_FOOT = 15

HEAT_MAP_X = 47
HEAT_MAP_Y = 38

DISPLAY_IMAGES = False


def get_latest_db():
    # assign directory
    directory = '*'

    # iterate over files in
    # that directory
    list_of_files = glob.glob(f'{directory}/*.sqlite3*')

    if len(list_of_files) == 0:
        print('Critical Error: No DB file found.')
        sys.exit()

    print('Found input files:')
    for filename in list_of_files:
        print(f'\t{filename}')
    latest_file = max(list_of_files, key=os.path.getctime)
    print(f'Latest file: {latest_file}')
    return latest_file


def sort_array(sub_li):
    l = len(sub_li)
    for i in range(0, l):
        for j in range(0, l - i - 1):

            if (sub_li[j][1] < sub_li[j + 1][1]):
                tempo = sub_li[j]
                sub_li[j] = sub_li[j + 1]
                sub_li[j + 1] = tempo

    return sub_li


def remove_emojis(df_bios):
    emoj = re.compile("["
                      u"\U0001F600-\U0001F64F"  # emoticons
                      u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                      u"\U0001F680-\U0001F6FF"  # transport & map symbols
                      u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                      u"\U00002500-\U00002BEF"  # chinese char
                      u"\U00002702-\U000027B0"
                      u"\U00002702-\U000027B0"
                      u"\U000024C2-\U0001F251"
                      u"\U0001f926-\U0001f937"
                      u"\U00010000-\U0010ffff"
                      u"\u2640-\u2642"
                      u"\u2600-\u2B55"
                      u"\u200d"
                      u"\u23cf"
                      u"\u23e9"
                      u"\u231a"
                      u"\ufe0f"  # dingbats
                      u"\u3030"
                      "]+", re.UNICODE)
    return re.sub(emoj, '', df_bios)


def generate_text_analysis(database_file):
    try:
        sqlite_connection = sqlite3.connect(database_file)
        cursor = sqlite_connection.cursor()

        # Getting all NAMES of Boulders and Routes:
        sql_query = """SELECT name FROM climbs WHERE layout_id = 1;"""
        # Creating cursor object using connection object
        cursor = sqlite_connection.cursor()
        # executing our sql query
        cursor.execute(sql_query)
        all_boulder_routes_name = cursor.fetchall()

        total_words = 0
        total_emojis = 0

        name_words_counts = dict()
        name_emoji_counts = dict()
        for boulder in all_boulder_routes_name:
            name = boulder[0]

            emoji_list = emojis.get(name)
            for emoji in emoji_list:
                total_emojis = total_emojis + 1
                if emoji in name_emoji_counts:
                    name_emoji_counts[emoji] = name_emoji_counts[emoji] + 1
                else:
                    name_emoji_counts[emoji] = 1

            name = remove_emojis(name)
            words = name.split()

            # Iterate through each word in the 'words' list.
            for word in words:
                word = word.lower()
                total_words = total_words + 1
                # Check if the word is already in the 'counts' dictionary.
                if word in name_words_counts:
                    # If the word is already in the dictionary, increment its frequency by 1.
                    name_words_counts[word] += 1
                else:
                    # If the word is not in the dictionary, add it to the dictionary with a frequency of 1.
                    name_words_counts[word] = 1

        name_words_counts = sorted(name_words_counts.items(), key=lambda x: x[1], reverse=True)
        name_words_counts = dict(name_words_counts)

        name_words_counts_table = PrettyTable()
        columns_word_table = ['#', 'Boulder Name Word', 'Repetitions', '%']
        name_words_counts_table.field_names = columns_word_table
        i = 1
        for w in name_words_counts:
            name_words_counts_table.add_row(
                [i, w, name_words_counts[w], '{:.3f}'.format(100 * name_words_counts[w] / total_words)])
            i = i + 1
        name_words_counts_table.align['Boulder Name Word'] = "r"
        name_words_counts_table.align['Repetitions'] = "l"

        with open('output/boulder_name_word_count.txt', 'w', encoding='utf-8') as w:
            w.write(str(name_words_counts_table))
        print('DONE: output/boulder_name_word_count.txt')

        word_keys = list(name_words_counts.keys())
        for i in range(0, 10):
            key = word_keys[i]
            print(f'{i + 1}\t{key}\t{name_words_counts[key]}')

        name_emoji_counts = sorted(name_emoji_counts.items(), key=lambda x: x[1], reverse=True)
        name_emoji_counts = dict(name_emoji_counts)

        # TODO: PrettyTables does not support emojis?
        with open('output/boulder_name_emoji_count.txt', 'w', encoding='utf-8') as w:
            w.write('#, Boulder Name Emoji\tRepetitions\t%\n')
            i = 1
            for e in name_emoji_counts:
                w.write(
                    f'{i}\t{e}\t{name_emoji_counts[e]}\t{'{:.3f}'.format(100 * name_emoji_counts[e] / total_emojis)}\n')
                i = i + 1
        print('DONE: output/boulder_name_emoji_count.txt')

        emoji_keys = list(name_emoji_counts.keys())
        for i in range(0, 10):
            key = emoji_keys[i]
            print(f'{i + 1}\t{key}\t{name_emoji_counts[key]}')

        cursor.close()

        # Generate Top WORDS table as PNG
        fig = plt.figure(figsize=(10, 10), dpi=300)
        ax = plt.subplot()

        ncols = len(columns_word_table)
        nrows = 20
        ax.set_xlim(0, ncols + 1)
        ax.set_ylim(0, nrows + 1)

        positions = [0.1, 0.5, 2.5, 3.5, 4.5]

        for i in range(0, 10):
            keys = list(name_words_counts.keys())
            key = keys[i]
            print(f'{i + 1}\t{key}\t{name_words_counts[key]}')

        # Add table's text
        for i in range(nrows):
            for j, column in enumerate(columns_word_table):

                table_index = nrows - i - 1
                key = word_keys[table_index]

                if j == 1:
                    ha = 'left'
                else:
                    ha = 'center'

                weight = 'normal'
                if j == 0:
                    text_label = str(table_index + 1)
                elif j == 1:
                    text_label = key

                elif j == 2:
                    text_label = name_words_counts[key]
                    weight = 'bold'
                elif j == 3:
                    text_label = '{:.3f}%'.format(100 * name_words_counts[key] / total_words)

                ax.annotate(
                    xy=(positions[j], i + .5),
                    text=text_label,
                    ha=ha,
                    va='center',
                    weight=weight
                )

        # Add column text (table header)
        for index, c in enumerate(columns_word_table):
            if index == 1:
                ha = 'left'
            else:
                ha = 'center'
            ax.annotate(
                xy=(positions[index], nrows + .25),
                text=columns_word_table[index],
                ha=ha,
                va='bottom',
                weight='bold'
            )

        # Add dividing lines
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [nrows, nrows], lw=1.5, color='black', marker='', zorder=4)
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [0, 0], lw=1.5, color='black', marker='', zorder=4)
        for x in range(1, nrows):
            ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [x, x], lw=1.15, color='gray', ls=':', zorder=3,
                    marker='')

        ax.set_axis_off()
        plt.savefig(
            'output/top_words_name_table.png',
            dpi=300,
            transparent=True,
            bbox_inches='tight'
        )

        # Generate Top EMOJI table as PNG

        columns_emoji_table = ['#', 'Boulder Name Emoji', 'Repetitions', '%']

        fig = plt.figure(figsize=(10, 10), dpi=300)
        ax = plt.subplot()

        ncols = len(columns_word_table)
        nrows = 20
        ax.set_xlim(0, ncols + 1)
        ax.set_ylim(0, nrows + 1)

        positions = [0.1, 0.5, 2.5, 3.5, 4.5]

        # Add table's text
        for i in range(nrows):
            for j, column in enumerate(columns_emoji_table):

                table_index = nrows - i - 1
                key = emoji_keys[table_index]

                if j == 1:
                    ha = 'left'
                else:
                    ha = 'center'

                weight = 'normal'
                if j == 0:
                    text_label = str(table_index + 1)
                elif j == 1:
                    text_label = key

                elif j == 2:
                    text_label = name_emoji_counts[key]
                    weight = 'bold'
                elif j == 3:
                    text_label = '{:.3f}%'.format(100 * name_emoji_counts[key] / total_emojis)

                ax.annotate(
                    xy=(positions[j], i + .5),
                    text=text_label,
                    ha=ha,
                    va='center',
                    weight=weight
                )

        # Add column text (table header)
        for index, c in enumerate(columns_emoji_table):
            if index == 1:
                ha = 'left'
            else:
                ha = 'center'
            ax.annotate(
                xy=(positions[index], nrows + .25),
                text=columns_emoji_table[index],
                ha=ha,
                va='bottom',
                weight='bold'
            )

        # Add dividing lines
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [nrows, nrows], lw=1.5, color='black', marker='', zorder=4)
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [0, 0], lw=1.5, color='black', marker='', zorder=4)
        for x in range(1, nrows):
            ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [x, x], lw=1.15, color='gray', ls=':', zorder=3,
                    marker='')

        ax.set_axis_off()
        plt.savefig(
            'output/top_emojis_name_table.png',
            dpi=300,
            transparent=True,
            bbox_inches='tight'
        )

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("The SQLite connection is closed")


def generate_users_analysis(database_file):
    try:
        sqlite_connection = sqlite3.connect(database_file)
        cursor = sqlite_connection.cursor()
        print("Database created and Successfully Connected to SQLite")

        sql_query = "select sqlite_version();"
        cursor.execute(sql_query)
        record = cursor.fetchall()

        print("SQLite Database Version is: ", record)
        cursor.close()

        # Creating cursor object using connection object
        cursor = sqlite_connection.cursor()
        # get unique values
        sql_query = """SELECT foreign_username, COUNT(*) 
                        FROM beta_links 
                        GROUP BY foreign_username;"""

        cursor.execute(sql_query)
        unique_users_video_uploader = cursor.fetchall()
        unique_users_video_uploader = sort_array(unique_users_video_uploader)

        users_video_uploader_table = PrettyTable()
        videos_columns = ['#', 'User Name', 'Uploaded Videos', '%']
        users_video_uploader_table.field_names = videos_columns

        total_videos = 0
        for user in unique_users_video_uploader:
            total_videos = total_videos + user[1]

        # Generate Top Setters table as PNG
        fig = plt.figure(figsize=(10, 10), dpi=300)
        ax = plt.subplot()

        ncols = len(videos_columns)
        nrows = 20
        ax.set_xlim(0, ncols + 1)
        ax.set_ylim(0, nrows + 1)

        positions = [0.1, 0.5, 2.5, 3.5, 4.5]

        # Add table's text
        for i in range(nrows):
            for j, column in enumerate(videos_columns):

                table_index = nrows - i - 1

                if j == 1:
                    ha = 'left'
                else:
                    ha = 'center'

                weight = 'normal'
                if j == 0:
                    text_label = str(table_index + 1)
                elif j == 1:
                    text_label = unique_users_video_uploader[table_index][0]

                elif j == 2:
                    text_label = unique_users_video_uploader[table_index][1]
                    weight = 'bold'
                elif j == 3:
                    text_label = '{:.3f}%'.format(100 * unique_users_video_uploader[table_index][1] / total_videos)

                ax.annotate(
                    xy=(positions[j], i + .5),
                    text=text_label,
                    ha=ha,
                    va='center',
                    weight=weight
                )

        # Add column text (table header)
        for index, c in enumerate(videos_columns):
            if index == 1:
                ha = 'left'
            else:
                ha = 'center'
            ax.annotate(
                xy=(positions[index], nrows + .25),
                text=videos_columns[index],
                ha=ha,
                va='bottom',
                weight='bold'
            )

        # Add dividing lines
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [nrows, nrows], lw=1.5, color='black', marker='', zorder=4)
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [0, 0], lw=1.5, color='black', marker='', zorder=4)
        for x in range(1, nrows):
            ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [x, x], lw=1.15, color='gray', ls=':', zorder=3, marker='')

        ax.set_axis_off()
        plt.savefig(
            'output/top_video_uploader_table.png',
            dpi=300,
            transparent=True,
            bbox_inches='tight'
        )

        i = 1
        for user in unique_users_video_uploader:
            users_video_uploader_table.add_row([i, user[0], user[1], '{:.3f}'.format(100 * user[1] / total_videos)])
            i = i + 1
        users_video_uploader_table.align['User Name'] = "l"
        users_video_uploader_table.align['Uploaded Videos'] = "l"

        with open('output/users_video_uploader_count.txt', 'w', encoding='utf-8') as w:
            w.write(str(users_video_uploader_table))
        print('DONE: output/users_video_uploader_count.txt')

        print(f'Total of video: {total_videos}')
        print(f'Total of video uploaders: {len(unique_users_video_uploader)}')
        print("List of top video uploaders:")
        for i in range(0, 10):
            print(f'{i + 1}\t{unique_users_video_uploader[i][1]}\t{unique_users_video_uploader[i][0]}')
        cursor.close()

        # Generate Setters Info
        cursor = sqlite_connection.cursor()
        # get unique values
        sql_query = """SELECT setter_username, COUNT(*) 
                                FROM climbs 
                                GROUP BY setter_username;"""

        cursor.execute(sql_query)
        unique_values_setter = cursor.fetchall()
        unique_values_setter = sort_array(unique_values_setter)

        print(f'Total of setter: {len(unique_values_setter)}')

        total_routes = 0
        for user in unique_values_setter:
            total_routes = total_routes + user[1]

        users_setters_table = PrettyTable()
        setter_columns = ['#', 'User Name', 'Boulder/routes', '%']
        users_setters_table.field_names = setter_columns
        i = 1
        for user in unique_values_setter:
            users_setters_table.add_row([i, user[0], user[1], '{:.3f}'.format(100 * user[1] / total_routes)])
            i = i + 1
        users_setters_table.align['User Name'] = "l"
        users_setters_table.align['Uploaded Videos'] = "l"

        # Generate Top Setters table as PNG
        fig = plt.figure(figsize=(10, 10), dpi=300)
        ax = plt.subplot()

        ncols = len(setter_columns)
        nrows = 20
        ax.set_xlim(0, ncols + 1)
        ax.set_ylim(0, nrows + 1)

        positions = [0.1, 0.5, 2.5, 3.5, 4.5]

        # Add table's text
        for i in range(nrows):
            for j, column in enumerate(setter_columns):

                table_index = nrows - i - 1
                if j == 1:
                    ha = 'left'
                else:
                    ha = 'center'

                weight = 'normal'
                if j == 0:
                    text_label = str(table_index + 1)
                elif j == 1:
                    text_label = unique_values_setter[table_index][0]

                elif j == 2:
                    text_label = unique_values_setter[table_index][1]
                    weight = 'bold'
                elif j == 3:
                    text_label = '{:.3f}%'.format(100 * unique_values_setter[table_index][1] / total_routes)

                ax.annotate(
                    xy=(positions[j], i + .5),
                    text=text_label,
                    ha=ha,
                    va='center',
                    weight=weight
                )

        # Add column text (table header)
        for index, c in enumerate(setter_columns):
            if index == 1:
                ha = 'left'
            else:
                ha = 'center'
            ax.annotate(
                xy=(positions[index], nrows + .25),
                text=setter_columns[index],
                ha=ha,
                va='bottom',
                weight='bold'
            )

        # Add dividing lines
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [nrows, nrows], lw=1.5, color='black', marker='', zorder=4)
        ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [0, 0], lw=1.5, color='black', marker='', zorder=4)
        for x in range(1, nrows):
            ax.plot([ax.get_xlim()[0], ax.get_xlim()[1]], [x, x], lw=1.15, color='gray', ls=':', zorder=3,
                    marker='')

        ax.set_axis_off()
        plt.savefig(
            'output/top_setters_table.png',
            dpi=300,
            transparent=True,
            bbox_inches='tight'
        )

        with open('output/users_setter_count.txt', 'w', encoding='utf-8') as w:
            w.write(str(users_setters_table))
        print('DONE: output/users_setter_count.txt')

        print(f'Total of boulders/routes: {total_routes}')
        print(f'Total of setters: {len(unique_values_setter)}')
        print('List of top video setters:')
        for i in range(0, 10):
            print(f'{i + 1}\t{unique_values_setter[i][1]}\t{unique_values_setter[i][0]}')
        cursor.close()

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("The SQLite connection is closed")


# Returns Array of 2D array: [Hold_ID, Hold_Role]
def get_holds_summary(boulder_string):
    # TODO: What are these char for?
    boulder_string = boulder_string.replace('"', '')
    boulder_string = boulder_string.replace(',', '')

    holds_summary = []
    while len(boulder_string) > 0:
        action = boulder_string[0]

        if action == 'p':
            hold_id = boulder_string[1:5]
            hold_role = boulder_string[6:8]

            holds_summary.append([hold_id, hold_role])

            boulder_string = boulder_string[8:]
        if action == 'x':
            boulder_string = boulder_string[5:]

    return holds_summary


def generate_board_array_numbers(data_array, title, file):
    # Remove number from 0 cells
    for x in range(HEAT_MAP_X):
        for y in range(HEAT_MAP_Y):
            if data_array[y, x] == 0:
                data_array[y, x] = None

    # get the board image as an array, so we can plot on top of it
    board_img = mpimg.imread('img.png')

    fig, ax = plt.subplots(figsize=(20, 20))

    sns.set()
    hmax = sns.heatmap(data_array,
                       cbar=False,
                       cmap=ListedColormap(['white']),
                       alpha=0,  # this makes heatmap translucent
                       annot=True,
                       fmt='.0f',
                       zorder=2,
                       annot_kws={'size': 8, 'color': 'blueviolet'},
                       )

    hmax.invert_yaxis()
    hmax.set_title(title)

    # heatmap uses pcolormesh instead of imshow, so we can't pass through
    # extent as a kwarg, so we can't match the heatmap to the map. Instead,
    # match the map to the heatmap:
    hmax.imshow(board_img,
                aspect=hmax.get_aspect(),
                extent=hmax.get_xlim() + hmax.get_ylim(),
                zorder=1)  # put the map under the heatmap

    plt.subplots_adjust(top=0.97, bottom=0.06, right=0.98, left=0.04)

    plt.title(title, fontsize=20)  # title with fontsize 20
    plt.xlabel('Board row', fontsize=15)  # x-axis label with fontsize 15
    plt.ylabel('Board column', fontsize=15)  # y-axis label with fontsize 15

    plt.savefig(file, dpi=300)
    if DISPLAY_IMAGES:
        plt.show()


def generate_board_heatmap(data_array, title, file):
    # Remove color from 0 cells
    for x in range(HEAT_MAP_X):
        for y in range(HEAT_MAP_Y):
            if data_array[y, x] == 0:
                data_array[y, x] = None

    # Define gradient for color map:
    # https://matplotlib.org/stable/gallery/color/colormap_reference.html
    wd = matplotlib.cm.cool._segmentdata  # only has R,G,B
    wd['alpha'] = ((0.0, 0.0, 0.3),
                   (0.3, 0.3, 1.0),
                   (1.0, 1.0, 1.0))
    color_map = LinearSegmentedColormap('kilterColormap', wd)

    # get the board image as an array, so we can plot on top of it
    board_img = mpimg.imread('img.png')

    fig, ax = plt.subplots(figsize=(20, 20))

    sns.set()

    if 'heatmap' in title.lower():
        hmax = sns.heatmap(data_array,
                           cmap=color_map,
                           alpha=0.6,  # this makes heatmap translucent
                           annot=False,
                           fmt='.0f',
                           zorder=2,
                           annot_kws={"size": 8},
                           )
    elif 'percentage' in title.lower():
        hmax = sns.heatmap(data_array,
                           cmap=color_map,
                           alpha=0.6,  # this makes heatmap translucent
                           annot=True,
                           fmt='.3%',
                           zorder=2,
                           annot_kws={"size": 8},
                           )
    else:
        hmax = sns.heatmap(data_array,
                           cmap=color_map,
                           alpha=0.6,  # this makes heatmap translucent
                           annot=True,
                           fmt='.0f',
                           zorder=2,
                           annot_kws={"size": 8},
                           )

    hmax.invert_yaxis()
    hmax.set_title(title)

    # heatmap uses pcolormesh instead of imshow, so we can't pass through
    # extent as a kwarg, so we can't match the heatmap to the map. Instead,
    # match the map to the heatmap:
    hmax.imshow(board_img,
                aspect=hmax.get_aspect(),
                extent=hmax.get_xlim() + hmax.get_ylim(),
                zorder=1)  # put the map under the heatmap

    plt.subplots_adjust(top=0.97, bottom=0.06, right=1.05, left=0.04)

    plt.title(title, fontsize=20)  # title with fontsize 20
    plt.xlabel('Board row', fontsize=15)  # x-axis label with fontsize 15
    plt.ylabel('Board column', fontsize=15)  # y-axis label with fontsize 15

    plt.savefig(file, dpi=300)
    if DISPLAY_IMAGES:
        plt.show()


def generate_heatmap(data_array, y_axis_labels, x_axis_labels, title, file):

    wd = matplotlib.cm.cool._segmentdata
    color_map = LinearSegmentedColormap('kilterColormap', wd)

    fig, ax = plt.subplots(figsize=(20, 20))

    if 'percentage' in title.lower():
        sns.heatmap(data_array,
                    xticklabels=x_axis_labels,
                    yticklabels=y_axis_labels,
                    linewidth=0.5,
                    ax=ax,
                    cmap=color_map,
                    annot=True,
                    fmt='.2%',
                    annot_kws={"size": 8}, )
    else:
        sns.heatmap(data_array,
                    xticklabels=x_axis_labels,
                    yticklabels=y_axis_labels,
                    linewidth=0.5,
                    ax=ax,
                    cmap=color_map,
                    annot=True,
                    fmt='.0f',
                    annot_kws={"size": 8}, )

    plt.subplots_adjust(top=0.97, bottom=0.05, right=1.05, left=0.12)

    plt.title(title, fontsize=20)  # title with fontsize 20
    plt.xlabel('Angles', fontsize=15)  # x-axis label with fontsize 15
    plt.ylabel('Grades', fontsize=15)  # y-axis label with fontsize 15

    plt.savefig(file, dpi=300)
    if DISPLAY_IMAGES:
        plt.show()


def make_bar_cart(x, y, title, y_axis_title, x_axis_title, filename):
    # Creates figure to customize
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create the graph
    sns.barplot(x=x, y=y)

    # Set a title
    ax.set_title(title, fontsize=14)
    ax.set_xlabel(x_axis_title, fontsize=14)
    ax.tick_params(axis='x', rotation=70)
    ax.set_ylabel(y_axis_title, fontsize=14)

    for i in ax.containers:
        if 'percentage' in title.lower():
            ax.bar_label(i, fontsize=8, fmt='%.1f%%')
        else:
            ax.bar_label(i, fontsize=8)

    if len(x) > 15:
        plt.subplots_adjust(top=0.95, bottom=0.26, right=0.97)
    else:
        plt.subplots_adjust(top=0.95, bottom=0.08, right=0.97)

    plt.savefig(filename)
    if DISPLAY_IMAGES:
        plt.show()


def generate_boulder_analysis(database_file):
    try:
        sqlite_connection = sqlite3.connect(database_file)
        cursor = sqlite_connection.cursor()

        sql_query = 'SELECT climb_uuid, angle, display_difficulty, ascensionist_count FROM climb_stats;'
        cursor.execute(sql_query)
        climb_stats = cursor.fetchall()

        grade_labels = ['4a/V0 or 5b/5.9', '4b/V0 or 5c/5.10a', '4c/V0 or 6a/5.10b', '5a/V1 or 6a+/5.10c',
                        '5b/V1 or 6b/5.10d', '5c/V2 or 6b+/5.11a', '6a/V3 or 6c/5.11b', '6a+/V3 or 6c+/5.11c',
                        '6b/V4 or 7a/5.11d', '6b+/V4 or 7a+/5.12a', '6c/V5 or 7b/5.12b', '6c+/V5 or 7b+/5.12c',
                        '7a/V6 or 7c/5.12d', '7a+/V7 or 7c+/5.13a', '7b/V8 or 8a/5.13b', '7b+/V8 or 8a+/5.13c',
                        '7c/V9 or 8b/5.13d', '7c+/V10 or 8b+/5.14a', '8a/V11 or 8c/5.14b', '8a+/V12 or 8c+/5.14c',
                        '8b/V13 or 9a/5.14d', '8b+/V14 or 9a+/5.15a', '8c/V15 or 9b/5.15b', '8c+/V16 or 9b+/5.15c']

        angle_labels = ['0°', '5°', '10°', '15°', '20°', '25°', '30°', '35°', '40°', '45°', '50°', '55°', '60°', '65°',
                        '70°']

        number_boulders_vs_grade_bar_chart_data = np.zeros(shape=24)
        number_ascents_vs_grade_bar_chart_data = np.zeros(shape=24)
        percent_boulders_vs_grade_bar_chart_data = np.zeros(shape=24)
        percent_ascents_vs_grade_bar_chart_data = np.zeros(shape=24)

        number_boulders_vs_angle_bar_chart_data = np.zeros(shape=15)
        number_ascents_vs_angle_bar_chart_data = np.zeros(shape=15)
        percent_boulders_vs_angle_bar_chart_data = np.zeros(shape=15)
        percent_ascents_vs_angle_bar_chart_data = np.zeros(shape=15)

        grade_angle_boulders_array = np.zeros(shape=(24, 15))
        grade_angle_ascents_array = np.zeros(shape=(24, 15))
        percent_grade_angle_boulders_array = np.zeros(shape=(24, 15))
        percent_grade_angle_ascents_array = np.zeros(shape=(24, 15))

        total_boulders = 0
        total_ascents = 0
        # Build hold dictionary with Hold ID, Hold X and Hold Y
        for climb_id, angle, difficulty, ascents in climb_stats:
            total_boulders = total_boulders + 1
            total_ascents = total_ascents + ascents

            grade_index = int(difficulty) - 10
            number_boulders_vs_grade_bar_chart_data[grade_index] = number_boulders_vs_grade_bar_chart_data[
                                                                       grade_index] + 1
            number_ascents_vs_grade_bar_chart_data[grade_index] = number_ascents_vs_grade_bar_chart_data[
                                                                      grade_index] + ascents

            angle_index = int(angle / 5)
            number_boulders_vs_angle_bar_chart_data[angle_index] = number_boulders_vs_angle_bar_chart_data[
                                                                       angle_index] + 1
            number_ascents_vs_angle_bar_chart_data[angle_index] = number_ascents_vs_angle_bar_chart_data[
                                                                      angle_index] + ascents

            grade_angle_boulders_array[grade_index, angle_index] = grade_angle_boulders_array[
                                                                       grade_index, angle_index] + 1
            grade_angle_ascents_array[grade_index, angle_index] = grade_angle_ascents_array[
                                                                      grade_index, angle_index] + ascents
        climb_stats = None

        for i, e in enumerate(number_boulders_vs_grade_bar_chart_data):
            percent_boulders_vs_grade_bar_chart_data[i] = 100 * e / total_boulders

        for i, e in enumerate(number_ascents_vs_grade_bar_chart_data):
            percent_ascents_vs_grade_bar_chart_data[i] = 100 * e / total_ascents

        for i, e in enumerate(number_boulders_vs_angle_bar_chart_data):
            percent_boulders_vs_angle_bar_chart_data[i] = 100 * e / total_boulders

        for i, e in enumerate(number_ascents_vs_angle_bar_chart_data):
            percent_ascents_vs_angle_bar_chart_data[i] = 100 * e / total_ascents

        # Generate BAR CHARTS:
        make_bar_cart(grade_labels,
                      number_boulders_vs_grade_bar_chart_data,
                      'Histogram Total Number Boulders/Routes vs Grade',
                      'Number of Boulders or Routes',
                      'Boulder Grade',
                      'output/histo_boulder_grade.png')

        make_bar_cart(grade_labels,
                      percent_boulders_vs_grade_bar_chart_data,
                      'Histogram Percentage Number Boulders/Routes vs Grade',
                      'Percentage of Boulders or Routes',
                      'Boulder Grade',
                      'output/histo_boulder_grade_percent.png')

        make_bar_cart(grade_labels,
                      number_ascents_vs_grade_bar_chart_data,
                      'Histogram Total Number Ascents vs Grade',
                      'Number of Ascents',
                      'Boulder Grade',
                      'output/histo_ascents_grade.png')

        make_bar_cart(grade_labels,
                      percent_ascents_vs_grade_bar_chart_data,
                      'Histogram Percentage Number Ascents vs Grade',
                      'Percentage of Ascents',
                      'Boulder Grade',
                      'output/histo_ascents_grade_percent.png')

        make_bar_cart(angle_labels,
                      number_boulders_vs_angle_bar_chart_data,
                      'Histogram Total Number Boulders/Routes vs Board Angle',
                      'Number of Boulders or Routes',
                      'Board Angle',
                      'output/histo_boulder_angle.png')

        make_bar_cart(angle_labels,
                      percent_boulders_vs_angle_bar_chart_data,
                      'Histogram Percentage Number Boulders/Routes vs Board Angle',
                      'Number of Ascents',
                      'Board Angle',
                      'output/histo_boulder_angle_percent.png')

        make_bar_cart(angle_labels,
                      number_ascents_vs_angle_bar_chart_data,
                      'Histogram Total Number Ascents',
                      'Number of Ascents',
                      'Board Angle',
                      'output/histo_ascents_angle.png')

        make_bar_cart(angle_labels,
                      percent_ascents_vs_angle_bar_chart_data,
                      'Histogram Percentage Ascents vs Bard Angle',
                      'Number of Ascents',
                      'Board Angle',
                      'output/histo_ascents_angle_percent.png')

        # Generate HEATMAPS
        for x in range(24):
            for y in range(15):
                percent_grade_angle_boulders_array[x, y] = grade_angle_boulders_array[x, y] / total_boulders
                percent_grade_angle_ascents_array[x, y] = grade_angle_ascents_array[x, y] / total_ascents

        generate_heatmap(grade_angle_boulders_array,
                         grade_labels,
                         angle_labels,
                         'Total Boulders Grade vs Angle',
                         'output/boulders_routes_grade_vs_angle.png')

        generate_heatmap(percent_grade_angle_boulders_array,
                         grade_labels,
                         angle_labels,
                         'Percentage Boulders Grade vs Angle',
                         'output/boulders_routes_grade_vs_angle_percent.png')

        generate_heatmap(grade_angle_ascents_array,
                         grade_labels,
                         angle_labels,
                         'Total Ascents Grade vs Angle',
                         'output/ascents_grade_vs_angle.png')

        generate_heatmap(percent_grade_angle_ascents_array,
                         grade_labels,
                         angle_labels,
                         'Percentage Ascents Grade vs Angle',
                         'output/ascents_grade_vs_angle_percent.png')

        # GET position for each board hold and build dictionary:
        sql_query = 'SELECT id, x, y FROM holes;'
        cursor.execute(sql_query)
        holds_position_table = cursor.fetchall()
        print(f'TOTAL hold/holes positions found: {len(holds_position_table)}')

        # Build hold dictionary with Hold ID, Hold X and Hold Y
        holds_dict = {}
        for hold_id, hold_x, hold_y in holds_position_table:
            holds_dict[str(hold_id)] = {
                'x': hold_x,
                'y': hold_y
            }
        holds_position_table = None

        sql_query = 'SELECT id, hole_id FROM placements WHERE layout_id = 1;'
        cursor.execute(sql_query)
        holds_placement_raw = cursor.fetchall()
        print(f'TOTAL holds placement found: {len(holds_placement_raw)}')

        # Add placement information to holds dictionary
        holds_placement = {}
        for placement_id, hold_id in holds_placement_raw:
            holds_placement[str(placement_id)] = str(hold_id)

            # add placement information to hold dictionary
            holds_dict[str(hold_id)]['placement_id'] = str(placement_id)
        holds_placement_raw = None

        holds_id_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        placement_id_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        for hold_id in holds_dict:
            x_value = int(int(holds_dict[hold_id]['x']) / 4) + 5
            y_value = int(int(holds_dict[hold_id]['y']) / 4) - 1

            if y_value < HEAT_MAP_Y and x_value < HEAT_MAP_X:
                holds_id_array[y_value, x_value] = int(hold_id)

                if 'placement_id' in holds_dict[hold_id]:
                    placement_id_array[y_value, x_value] = int(holds_dict[hold_id]['placement_id'])

        generate_board_array_numbers(holds_id_array, 'Holds ID', 'output/hold_id.png')
        generate_board_array_numbers(placement_id_array, 'Placement ID', 'output/placement_id.png')

        # GET all BOULDER lines + ROUTES lines from DDBB:
        sql_query = 'SELECT * FROM climbs WHERE layout_id = 1 AND is_listed = 1;'

        cursor.execute(sql_query)
        boulder_layout_1 = cursor.fetchall()
        print(f'TOTAL boulders + routes found: {len(boulder_layout_1)}')

        master_hold_summary_starts = {}
        master_hold_summary_tops = {}
        master_hold_summary_hands = {}
        master_hold_summary_foots = {}

        total_starts_holds = 0
        total_tops_holds = 0
        total_hands_holds = 0
        total_foots_holds = 0

        for i in range(len(boulder_layout_1)):

            line_summary = get_holds_summary(boulder_layout_1[i][14])

            for hold_array in line_summary:

                hold_placement_id = hold_array[0]
                hold_role = hold_array[1]
                hold_id = holds_placement[hold_placement_id]

                match hold_role:
                    case '12' | '20' | '24' | '28' | '32' | '39' | '42':  # ROLE_START

                        total_starts_holds = total_starts_holds + 1

                        if hold_id in master_hold_summary_starts:
                            h = master_hold_summary_starts[hold_id]
                            h['count'] = h['count'] + 1
                            master_hold_summary_starts[hold_id] = h
                        else:

                            array_y = int(int(holds_dict[hold_id]['y']) / 4) - 1
                            array_x = int(int(holds_dict[hold_id]['x']) / 4) + 5

                            master_hold_summary_starts[hold_id] = {'hold_id': hold_id,
                                                                   'placement_id': hold_placement_id,
                                                                   'hold_role': hold_role,
                                                                   'count': 1,
                                                                   'x': array_x,
                                                                   'y': array_y
                                                                   }
                    case '13' | '21' | '25' | '29' | '33' | '36' | '37' | '41' | '43':  # ROLE_HAND

                        total_hands_holds = total_hands_holds + 1

                        if hold_id in master_hold_summary_hands:
                            h = master_hold_summary_hands[hold_id]
                            h['count'] = h['count'] + 1
                            master_hold_summary_hands[hold_id] = h
                        else:

                            array_y = int(int(holds_dict[hold_id]['y']) / 4) - 1
                            array_x = int(int(holds_dict[hold_id]['x']) / 4) + 5

                            master_hold_summary_hands[hold_id] = {'hold_id': hold_id,
                                                                  'placement_id': hold_placement_id,
                                                                  'hold_role': hold_role,
                                                                  'count': 1,
                                                                  'x': array_x,
                                                                  'y': array_y
                                                                  }

                    case '14' | '22' | '26' | '30' | '34' | '44':  # ROLE_FINISH / TOP

                        total_tops_holds = total_tops_holds + 1

                        if hold_id in master_hold_summary_tops:
                            h = master_hold_summary_tops[hold_id]
                            h['count'] = h['count'] + 1
                            master_hold_summary_tops[hold_id] = h
                        else:

                            array_y = int(int(holds_dict[hold_id]['y']) / 4) - 1
                            array_x = int(int(holds_dict[hold_id]['x']) / 4) + 5

                            master_hold_summary_tops[hold_id] = {'hold_id': hold_id,
                                                                 'placement_id': hold_placement_id,
                                                                 'hold_role': hold_role,
                                                                 'count': 1,
                                                                 'x': array_x,
                                                                 'y': array_y
                                                                 }

                    case '15' | '23' | '27' | '31' | '35' | '45':  # ROLE_FOOT

                        total_foots_holds = total_foots_holds + 1

                        if hold_id in master_hold_summary_foots:
                            h = master_hold_summary_foots[hold_id]
                            h['count'] = h['count'] + 1
                            master_hold_summary_foots[hold_id] = h
                        else:

                            array_y = int(int(holds_dict[hold_id]['y']) / 4) - 1
                            array_x = int(int(holds_dict[hold_id]['x']) / 4) + 5

                            master_hold_summary_foots[hold_id] = {'hold_id': hold_id,
                                                                  'placement_id': hold_placement_id,
                                                                  'hold_role': hold_role,
                                                                  'count': 1,
                                                                  'x': array_x,
                                                                  'y': array_y
                                                                  }

                    case _:
                        print(f'Warining: Unkown role! {hold_role} for placement_id: {hold_placement_id}')
                        print(boulder_layout_1[i])

        cursor.close()

        starts_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        starts_percent_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        for p in master_hold_summary_starts:
            x_value = int(master_hold_summary_starts[p]['x'])
            y_value = int(master_hold_summary_starts[p]['y'])
            count = int(master_hold_summary_starts[p]['count'])

            # Actually there are boulders with holds out of board boundaries
            # You can check on application: Extension by DrPlim
            if y_value <= HEAT_MAP_Y and x_value <= HEAT_MAP_X:
                starts_array[y_value, x_value] = count
                starts_percent_array[y_value, x_value] = count / total_starts_holds
        starts_array_smooth = gaussian_filter(starts_array, sigma=2)

        top_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        top_percent_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        for p in master_hold_summary_tops:
            x_value = int(master_hold_summary_tops[p]['x'])
            y_value = int(master_hold_summary_tops[p]['y'])
            count = int(master_hold_summary_tops[p]['count'])

            if y_value <= HEAT_MAP_Y and x_value <= HEAT_MAP_X:
                top_array[y_value, x_value] = count
                top_percent_array[y_value, x_value] = count / total_tops_holds
        top_array_smooth = gaussian_filter(top_array, sigma=2)

        hands_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        hands_percent_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        for p in master_hold_summary_hands:
            x_value = int(master_hold_summary_hands[p]['x'])
            y_value = int(master_hold_summary_hands[p]['y'])
            count = int(master_hold_summary_hands[p]['count'])

            if y_value <= HEAT_MAP_Y and x_value <= HEAT_MAP_X:
                hands_array[y_value, x_value] = count
                hands_percent_array[y_value, x_value] = count / total_hands_holds
        hands_array_smooth = gaussian_filter(hands_array, sigma=2)

        foot_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        foot_percent_array = np.zeros(shape=(HEAT_MAP_Y, HEAT_MAP_X))
        for p in master_hold_summary_foots:
            x_value = int(master_hold_summary_foots[p]['x'])
            y_value = int(master_hold_summary_foots[p]['y'])
            count = int(master_hold_summary_foots[p]['count'])
            if y_value <= HEAT_MAP_Y and x_value <= HEAT_MAP_X:
                foot_array[y_value, x_value] = count
                foot_percent_array[y_value, x_value] = count / total_foots_holds
        foot_array_smooth = gaussian_filter(foot_array, sigma=2)

        generate_board_heatmap(starts_array,
                               'Total Numbers Boulders/Routes with START hold',
                               'output/starts_array.png')

        generate_board_heatmap(starts_percent_array,
                               'Percentage Numbers Boulders/Routes with START hold',
                               'output/starts_percent_array.png')

        generate_board_heatmap(starts_array_smooth,
                               'START hold heatmap',
                               'output/starts_heatmap_array.png')

        generate_board_heatmap(top_array,
                               'Total Numbers Boulders/Routes with TOP hold',
                               'output/top_array.png')

        generate_board_heatmap(top_percent_array,
                               'Percentage Numbers Boulders/Routes with TOP hold',
                               'output/top_percent_array.png')

        generate_board_heatmap(top_array_smooth,
                               'TOP hold heatmap',
                               'output/top_heatmap_array.png')

        generate_board_heatmap(hands_array,
                               'Total Numbers Boulders/Routes with HAND hold',
                               'output/hands_array.png')

        generate_board_heatmap(hands_percent_array,
                               'Percentage Numbers Boulders/Routes with HAND hold',
                               'output/hands_percent_array.png')

        generate_board_heatmap(hands_array_smooth,
                               'HAND hold heatmap',
                               'output/hands_heatmap_array.png')

        generate_board_heatmap(foot_array,
                               'Total Numbers Boulders/Routes with START hold',
                               'output/foot_array.png')

        generate_board_heatmap(foot_percent_array,
                               'Percentage Numbers Boulders/Routes with FOOT hold',
                               'output/foot_percent_array.png')

        generate_board_heatmap(foot_array_smooth,
                               'FOOT hold heatmap',
                               'output/foot_heatmap_array.png')

        hold_summary_starts_table = PrettyTable()
        hold_summary_starts_table.field_names = ['#', 'hold_id', 'placement_id', 'hold_role', 'x', 'y', 'count']
        i = 1
        for w in master_hold_summary_starts:
            hold_summary_starts_table.add_row(
                [i,
                 master_hold_summary_starts[w]['hold_id'],
                 master_hold_summary_starts[w]['placement_id'],
                 master_hold_summary_starts[w]['hold_role'],
                 master_hold_summary_starts[w]['x'],
                 master_hold_summary_starts[w]['y'],
                 master_hold_summary_starts[w]['count']])
            i = i + 1
        with open('output/hold_summary_starts_table.txt', 'w', encoding='utf-8') as w:
            w.write(str(hold_summary_starts_table))
        print('DONE: output/hold_summary_starts_table.txt')

        hold_summary_tops_table = PrettyTable()
        hold_summary_tops_table.field_names = ['#', 'hold_id', 'placement_id', 'hold_role', 'x', 'y', 'count']
        i = 1
        for w in master_hold_summary_tops:
            hold_summary_tops_table.add_row(
                [i,
                 master_hold_summary_tops[w]['hold_id'],
                 master_hold_summary_tops[w]['placement_id'],
                 master_hold_summary_tops[w]['hold_role'],
                 master_hold_summary_tops[w]['x'],
                 master_hold_summary_tops[w]['y'],
                 master_hold_summary_tops[w]['count']])
            i = i + 1
        with open('output/hold_summary_tops_table.txt', 'w', encoding='utf-8') as w:
            w.write(str(hold_summary_tops_table))
        print('DONE: output/hold_summary_tops_table.txt')

        hold_summary_hands_table = PrettyTable()
        hold_summary_hands_table.field_names = ['#', 'hold_id', 'placement_id', 'hold_role', 'x', 'y', 'count']
        i = 1
        for w in master_hold_summary_hands:
            hold_summary_hands_table.add_row(
                [i,
                 master_hold_summary_hands[w]['hold_id'],
                 master_hold_summary_hands[w]['placement_id'],
                 master_hold_summary_hands[w]['hold_role'],
                 master_hold_summary_hands[w]['x'],
                 master_hold_summary_hands[w]['y'],
                 master_hold_summary_hands[w]['count']])
            i = i + 1
        with open('output/hold_summary_hands_table.txt', 'w', encoding='utf-8') as w:
            w.write(str(hold_summary_hands_table))
        print('DONE: output/hold_summary_hands_table.txt')

        hold_summary_foots_table = PrettyTable()
        hold_summary_foots_table.field_names = ['#', 'hold_id', 'placement_id', 'hold_role', 'x', 'y', 'count']
        i = 1
        for w in master_hold_summary_foots:
            hold_summary_foots_table.add_row(
                [i,
                 master_hold_summary_foots[w]['hold_id'],
                 master_hold_summary_foots[w]['placement_id'],
                 master_hold_summary_foots[w]['hold_role'],
                 master_hold_summary_foots[w]['x'],
                 master_hold_summary_foots[w]['y'],
                 master_hold_summary_foots[w]['count']])
            i = i + 1
        with open('output/hold_summary_foots_table.txt', 'w', encoding='utf-8') as w:
            w.write(str(hold_summary_foots_table))
        print('DONE: output/hold_summary_foots_table.txt')

        with open('output/master_hold_summary_starts.json', 'w') as outfile:
            json.dump(master_hold_summary_starts, outfile, indent=4)
        with open('output/master_hold_summary_tops.json', 'w') as outfile:
            json.dump(master_hold_summary_tops, outfile, indent=4)
        with open('output/master_hold_summary_hands.json', 'w') as outfile:
            json.dump(master_hold_summary_hands, outfile, indent=4)
        with open('output/master_hold_summary_foots.json', 'w') as outfile:
            json.dump(master_hold_summary_foots, outfile, indent=4)

    except sqlite3.Error as error:
        print("Error while connecting to sqlite", error)
    finally:
        if sqlite_connection:
            sqlite_connection.close()
            print("The SQLite connection is closed")


def main(argv, null=None):
    inputfile = ''
    outputfile = ''

    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])

    except getopt.GetoptError:
        print('ERROR (getopt.GetoptError): kilter_nerd.py -i <inputfile> -o <outputfile>')
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print('kilter_nerd.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-i", "--ifile"):
            inputfile = arg
        elif opt in ("-o", "--ofile"):
            outputfile = arg

    if not inputfile:
        print("No input file! looking for latest DDBB")
        inputfile = get_latest_db()

    print('Input file is "', inputfile)
    print('Output file is (not used)"', outputfile)

    generate_text_analysis(inputfile)
    generate_users_analysis(inputfile)
    generate_boulder_analysis(inputfile)

if __name__ == "__main__":
    main(sys.argv[1:])
    print('done')
