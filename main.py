import requests
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import plotly.express as px
import geopandas as gpd
from shapely.geometry import Point
import sqlite3
import os
from gtts import gTTS
from bs4 import BeautifulSoup

with st.echo(code_location='below'):
    def build_aqi_plot(input_cities):
        entrypoint = "http://api.waqi.info/feed/"
        pars = {
            'token': '4e61e4e4579aae5aeb921cb9e8897fc483b2380c'
        }
        cities_list = pd.Series(dtype='float64')
        for city in input_cities:
            r = requests.get(entrypoint + city, params=pars).json()
            cities_list[city] = float(r['data']['aqi'])
        cities_list_sorted = cities_list.sort_values(ascending=True)
        df = pd.DataFrame({'name': np.array(cities_list_sorted.index)[::-1], 'values': np.array(cities_list_sorted.values)[::-1]})
        fig = sns.barplot(x='values', y='name', data=df)
        st.pyplot(plt, clear_figure=True)
        city = cities_list_sorted.index[-1]
        entrypoint = "https://wikipedia.org/wiki/"
        s = BeautifulSoup(requests.get(entrypoint + city).text, features="html.parser")
        st.write(city)
        for a in s.find_all('tr', {'class': 'mergedtoprow'}):
            if len(a.text) > 7 and a.text[:7] == 'Country':
                st.write('Country: ', a.text[7:])
        for a in s.find_all('tr', {'class': 'mergedrow'}):
            if a.text[3:8] == 'Total':
                # st.write(a.text[8:])
                potential = a.text[8:].split(',')
                # st.write(potential)
                if all(map(lambda x: x.isdigit(), potential)):
                    st.write('Population: ', int(''.join(potential)))
            elif a.text[3:7] == 'Rank':
                st.write('Population Rank in country: ', a.text[7:])
            elif a.text[3:7] == 'Type':
                st.write('Government type: ', a.text[7:])


    def build_dynamic_plot(df, chosen_countries, select_type, select_show):
        chosen_df = df[df['Entity'].isin(chosen_countries)]
        chosen_df = chosen_df.rename(columns={
            'air pollution': 'Смерти от общего загрязнения воздуха',
            'household solid fuels': 'Смерти от твердого топлива',
            'ambient particulate': 'Смерти от атмосферных твердых частиц',
            'ambient ozone': 'Смерти от атмосферного озона',
        })
        type_of_compare = ''
        if select_type == 'Общее загрязнение воздуха':
            type_of_compare = 'Смерти от общего загрязнения воздуха'
        elif select_type == 'Твердое топливо':
            type_of_compare = 'Смерти от твердого топлива'
        elif select_type == 'Атмосферные твердые частицы':
            type_of_compare = 'Смерти от атмосферных твердых частиц'
        elif select_type == 'Атмосферный озон':
            type_of_compare = 'Смерти от атмосферного озона'

        chosen_df = chosen_df.rename(columns={'Entity': 'Страны', 'Year': 'Год'})
        if select_show == 'Буквально каждый год':
            figure = px.bar(chosen_df, x='Страны', y=type_of_compare, color='Страны', animation_frame='Год')
        elif select_show == 'В совокупности за прошедшие года':
            for country in chosen_countries:
                chosen_df.loc[chosen_df['Страны'] == country, type_of_compare] = chosen_df.loc[chosen_df['Страны'] == country, type_of_compare].cumsum()
            figure = px.bar(chosen_df, x='Страны', y=type_of_compare, color='Страны', animation_frame='Год')
        st.plotly_chart(figure)


    def build_pie_plot(year, compare_object):
        df = pd.read_csv('2003_2017_waste.csv')
        if compare_object == 'Не переработанные отходы в тоннах':
            compare_object = 'waste_disposed_of_tonne'
        elif compare_object == 'Переработанные отходы в тоннах':
            compare_object = 'total_waste_recycled_tonne'
        elif compare_object == 'Образующиеся отходы в тоннах':
            compare_object = 'total_waste_generated_tonne'
        elif compare_object == 'Recycling rate':
            compare_object = 'recycling_rate'
        df_drop = df[df['year'] == year]
        df_drop = df_drop[df_drop['waste_type'] != 'Total']
        fig = px.pie(df_drop, values=compare_object, names='waste_type')
        fig.update_traces(textposition='inside')
        fig.update_layout(uniformtext_minsize=12, uniformtext_mode='hide')
        st.plotly_chart(fig)


    def build_temp_plot(df, chosen_months):
        if len(chosen_months) > 0:
            years = df['Year'].values[:-1]
            df.set_index('Year', inplace=True)
            df = df.drop([2016])
            for i in df.columns[:12]:
                df[i] = pd.to_numeric(df[i])
            df = df.loc[:, chosen_months]
            new_df = pd.DataFrame(columns=['year', 'temp'])
            for month in chosen_months:
                new_df = pd.concat([new_df, pd.DataFrame({'year': years, 'temp': df[month].values})])
            new_df = new_df.astype('float64')
            figure = sns.regplot(x='year', y='temp', data=new_df, scatter_kws={'s': 3}, line_kws={'color': 'red'}, order=2)
            figure.set(xlabel='год', ylabel='температура')
            st.pyplot(plt, clear_figure=True)


    def build_map(choice, slide, type_of_map):
        conn = sqlite3.connect("database.sqlite")
        c = conn.cursor()
        df = pd.read_csv('cities_air_quality_water_pollution_18-10-2021.csv')
        c.execute(
            """
            DROP TABLE IF EXISTS df
            """
        )
        c.execute(
            """
            DROP TABLE IF EXISTS cities_coords
            """
        )
        df.rename(columns={' "AirQuality"': 'Air Quality', ' "WaterPollution"': 'Water Pollution'}, inplace=True)
        if choice == 'Загрязнение воздуха':
            choice = 'Air Quality'
        elif choice == 'Загрязнение воды':
            choice = 'Water Pollution'
        df = df[df[choice] > slide]
        cities_coordinates = pd.read_csv('worldcities.csv')
        df.to_sql("df", conn)
        cities_coordinates.to_sql("cities_coords", conn)
        ready_df = pd.read_sql(
            """
            SELECT df.City, lng, lat FROM df
            INNER JOIN cities_coords
            ON df.City == cities_coords.city
            GROUP BY df.City
            """,
            conn,
        )
        ready_df['lat'] = pd.to_numeric(ready_df['lat'])
        ready_df['lng'] = pd.to_numeric(ready_df['lng'])
        ready_df.rename(columns={'lng': 'lon'}, inplace=True)
        cities_gdf = gpd.GeoDataFrame(geometry=[Point(obj['lon'], obj['lat']) for _, obj in ready_df.iterrows()])
        world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
        base = world.plot(color='white', edgecolor='black')
        c = cities_gdf.plot(ax=base, marker='o', color='red', markersize=5)
        if type_of_map == 'С помощью GeoPandas':
            st.pyplot(plt, clear_figure=True)
        elif type_of_map == 'С помощью St.Map':
            st.map(ready_df)

    def main():
        st.write("""
        ## Мой проект посвящен одним из актуальных проблем современного мира - экологическим проблемам. Ниже представлены визуализации, иллюстрирующие уровень качества воздуха, количество смертей от загрязнения воздуха, количество переработанных отходов в Сингапуре, одной из самых богатых стран, а также визуализация, посвященная глобальному потеплению. Помимо визуальной информации я предлагаю также получить и звуковую, вы можете прослушать интересные экологические факты.
        #### Первая визуализация иллюстрирует AQI – air quality index – индекс качества воздуха, используемый для информирования населения про уровень загрязнения воздуха. То есть данная визуализация показывает качество воздуха в различных городах мира на данный момент (в прямом эфире). Интереснее всего посмотреть на следующие города: одни из самых загрязненных - Bhiwadi, Hotan, Moscow, Dhaka, и одни из самых густонаселенных - New York, Seoul, Shanghai, Mumbai, Istanbul, Tokyo, Lagos или New Delhi, хотя можно взять и любые другие.
        """)
        st.write("""
        ##### Здесь можно прослушать интересный факт про воздух.
        """)
        s = 0
        if os.path.isfile('visual_1.wav'):
            sound = open('visual_1.wav', 'rb')
            s = sound.read()
        else:
            tts = gTTS(
                'Характеризующиеся особой влажностью лесА Амазонки выделяют около 20% мирового запаса кислорода.',
                lang='ru')
            tts.save('visual_1.wav')
            sound = open('visual_1.wav', 'rb')
            s = sound.read()
        st.audio(s, format="audio/wav")

        number_of_cities = st.number_input('Выбери количество стран', min_value=1, max_value=30, step=1)
        input_cities = []
        with st.form('123'):
            for i in range(number_of_cities):
                input_cities.append(st.text_input(f'Введи город №{i + 1}'))
            sumbit = st.form_submit_button(label='AQI')
        if sumbit:
                build_aqi_plot(input_cities)


        st.write("""
        #### Вторая визуализация иллюстрирует динамическое изменение количества смертей от загрязнений воздуха в различных странах из года в год. Можно выбрать конкретную причину смерти людей, то есть от воздействия твердого топлива, атмосферных твердых частиц или от атмосферного озона. Также можно посмотреть эту статистику в совокупности.
         """)
        st.write("""
        ##### Здесь можно прослушать интересный факт про загрязнение воздуха.
        """)
        s = 0
        if os.path.isfile('visual_2.wav'):
            sound = open('visual_2.wav', 'rb')
            s = sound.read()
        else:
            tts = gTTS(
                'В Китае воздух настолько загрязнён, что людям, которые провели целый день на улице, намного полезнее было бы выкурить две пачки «легких» или одну пачку «тяжелых» сигарет!',
                lang='ru')
            tts.save('visual_2.wav')
            sound = open('visual_2.wav', 'rb')
            s = sound.read()
        st.audio(s, format="audio/wav")
        df_death = pd.read_csv('death-rates-from-air-pollution.csv')
        df_death = df_death.rename(columns={df_death.columns[3]: 'air pollution', df_death.columns[4]: 'household solid fuels', df_death.columns[5]: 'ambient particulate', df_death.columns[6]: 'ambient ozone'})
        countries = df_death['Entity'].unique()
        chosen_countries = st.multiselect('Выбери страны', countries)
        select_type = st.radio('Выбери тип загрязнения', ('Общее загрязнение воздуха', 'Твердое топливо', 'Атмосферные твердые частицы', 'Атмосферный озон'))
        select_show = st.radio('Выбери категорию', ('Буквально каждый год', 'В совокупности за прошедшие года'))
        build_dynamic_plot(df_death, chosen_countries, select_type, select_show)

        st.write("""
        #### Следующая визуализация также посвящена загрязнению окружающей среды. Здесь рассматривается уровень загрязнения воздуха и воды в различных городах, далее можно выбрать интересующий вас уровень загрязнения и после этого на карте появятся точки, символизирующие города с бОльшим уровнем загрязнения. То есть, если выбрать уровень 20, то на карте покажутся все города с уровнем загрязнения больше 20. Нормой считается уровень загрязнения от 0 до 50.   
        """)
        st.write("""
        ##### Здесь можно прослушать интересный факт про загрязнение воды.
        """)
        s = 0
        if os.path.isfile('visual_3.wav'):
            sound = open('visual_3.wav', 'rb')
            s = sound.read()
        else:
            tts = gTTS(
                'Ежегодно в воды Мирового океана попадает около 260 миллионов тонн изделий из пластмассы и пластика.',
                lang='ru')
            tts.save('visual_3.wav')
            sound = open('visual_3.wav', 'rb')
            s = sound.read()
        st.audio(s, format="audio/wav")
        choice = st.radio('Выбери тип загрязнения', ['Загрязнение воздуха', 'Загрязнение воды'])
        slide = st.slider('Выбери уровень загрязнения', min_value=0, max_value=100, value=50)
        type_of_map = st.radio('Выбери тип карты', ['С помощью GeoPandas', 'С помощью St.Map'])
        build_map(choice, slide, type_of_map)

        st.write("""
        #### Следующая визуализация посвящена переработке отходов в Сингапуре, одной из богатейших и красивейших стран в мире. Здесь можно посмотреть на доли не переработанного мусора, также можно увидеть какие доли приходятся на переработку того или иного типа отходов в любом году с 2003 по 2017. 
        """)
        st.write("""
        ##### Здесь можно прослушать интересный факт про переработку отходов.
        """)
        s = 0
        if os.path.isfile('visual_4.wav'):
            sound = open('visual_4.wav', 'rb')
            s = sound.read()
        else:
            tts = gTTS(
                'Шведы покупают у других стран мусор, а затем перерабатывает его и используют для получения электроэнергии. Только 4 5 процентов мусора в Швеции закапывается в землю, остальные 95 96 процентов становятся источником достаточно дешевой энергии.',
                lang='ru')
            tts.save('visual_4.wav')
            sound = open('visual_4.wav', 'rb')
            s = sound.read()
        st.audio(s, format="audio/wav")
        year = st.number_input('Выбери год', min_value= 2003, max_value=2017, step=1)
        compare_object = st.radio('Выбери тип', ('Не переработанные отходы в тоннах', 'Переработанные отходы в тоннах', 'Образующиеся отходы в тоннах'))
        build_pie_plot(year, compare_object)

        st.write("""
        #### Последняя визуализация на тему глобального потепления иллюстрирует отклонение температуры земли от нормы в разные месяцы года, для детального рассмотрения отклонения можно выбрать интересующие вас конкретные месяцы.
        """)
        st.write("""
        ##### Здесь можно прослушать интересный факт про глобальное потепление.
            """)
        s = 0
        if os.path.isfile('visual_5.wav'):
            sound = open('visual_5.wav', 'rb')
            s = sound.read()
        else:
            tts = gTTS(
                'Если средняя мировая годовая температура во всем мире повысится на 4 5 градусов, то леса исчезнут практически по всей территории Российской Федерации и в некоторых странах в Европе.',
                lang='ru')
            tts.save('visual_5.wav')
            sound = open('visual_5.wav', 'rb')
            s = sound.read()
        st.audio(s, format="audio/wav")
        df_temp = pd.read_csv('GLB_Ts_dSST.csv')
        choice_months = st.radio('Выбери тип', ('Рассмотреть все месяцы', 'Рассмотреть только несколько месяцев'))
        chosen_months = []
        if choice_months == 'Рассмотреть все месяцы':
            chosen_months = df_temp.columns[1:13]
        elif choice_months == 'Рассмотреть только несколько месяцев':
            chosen_months = st.multiselect('Выбери месяцы', df_temp.columns[1:13], ['Jan'])
        build_temp_plot(df_temp, chosen_months)
        st.write("""
        В работе реализованы следующие технологии: обработка данных с помощью pandas, веб-скреппинг, REST API, математические возможности Python, SQL, geopandas, библиотека qtts для работы с аудиофайлами.
        """)


    if __name__ == '__main__':
        main()