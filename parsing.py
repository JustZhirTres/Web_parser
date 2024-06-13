import requests
from bs4 import BeautifulSoup
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.orm import sessionmaker
import logging
# matplotlib.use('Agg')
import matplotlib.pyplot as plt
import configparser


def read_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    database_url = config.get('database', 'url')
    log_file = config.get('logging', 'file')
    log_level = config.get('logging', 'level')
    web_port = config.get('web', 'port')

    return database_url, log_file, log_level, web_port


DB_URL, LOG_FILE, LOG_LEVEL, WEB_PORT = read_config('config.ini')
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(filename=LOG_FILE, level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)

engine = create_engine(DB_URL)
Base = sqlalchemy.orm.declarative_base()
Base.metadata.create_all(engine)
base_url = "https://roundranking.com/final/ranking-json22r.php?year={}&sc=All%20Countries&sa=SO&s=O"


class University(Base):
    __tablename__ = 'universities'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    location = Column(String)


class Rating(Base):
    __tablename__ = 'ratings'
    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey('universities.id'))
    year = Column(Integer)
    rank = Column(Integer)
    score = Column(Integer)


Session = sessionmaker(bind=engine)
session = Session()

# Итерируемся по годам и парсим данные
for year in range(2020, 2024):
    url = base_url.format(year)

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            x = 0
            for university in data:
                # Проверяем, существует ли уже университет
                uni = session.query(University).filter_by(name=university["univ"]).first()
                if not uni:
                    uni = University(name=university["univ"], location=university["economy"])
                    session.add(uni)
                    session.commit()

                rating = Rating(university_id=uni.id, year=year, rank=university["i"], score=university["score"])
                session.add(rating)

            session.commit()
            logging.info(f"Data for year {year} has been stored in the database.")
        else:
            logging.error(f"Failed to fetch data for year {year}. Status code: {response.status_code}")
    except Exception as e:
        logging.error(f"An error occurred while processing data for year {year}: {str(e)}")

top_universities = session.query(University).join(Rating).group_by(University.id).order_by(Rating.rank).limit(20).all()
# top_20_ratings = session.query(Rating).filter(Rating.rank <= 20).all()

for university in top_universities:
    ratings = session.query(Rating).filter_by(university_id=university.id).order_by(Rating.year).all()
    years = [rating.year for rating in ratings]
    ranks = [rating.rank for rating in ratings]

    plt.plot(years, ranks, label=university.name)


print("Plot is loading...")
print("The plot is displayed in a separate window")

plt.xlabel('Year')
plt.ylabel('Rank')
plt.title('Top 20 Universities Rankings')
plt.legend(loc='lower right', prop={'size': 8})
plt.gca().invert_yaxis()
plt.show()

print("Data processing completed.")
