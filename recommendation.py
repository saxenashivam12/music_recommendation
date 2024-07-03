import csv
from abc import ABC, abstractmethod, ABCMeta

IGNORABLE_ATTRIBUTES_FOR_ITERABLE = ['_name', '_similarity_score', '_set_of_song_names_with_scores']
similarity_based_songs_metadata = list()
song_names = set()


class Iter(object):
    def __iter__(self):
        for attr, value in self.__dict__.items():
            if attr not in IGNORABLE_ATTRIBUTES_FOR_ITERABLE:
                yield attr, value


class SingletonABCMeta(ABCMeta):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonABCMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Song(Iter):
    def __init__(self, name, genre, tempo, singer, release_year):
        self._name = name
        self._singer = singer
        self._release_year = release_year
        self._genre = genre
        self._tempo = tempo

    def get_name(self):
        return self._name

    def get_singer(self):
        return self._singer

    def get_release_year(self):
        return self._release_year

    def get_genre(self):
        return self._genre

    def get_tempo(self):
        return self._tempo

    def __str__(self):
        return f'Song name: {self._name}, genre: {self._genre}, tempo: {self._tempo}, ' \
               f'singer: {self._singer}, release year: {self._release_year}'


class SimilarityIndexBasedSongRecommendation(Song):
    def __init__(self, name, genre, tempo, singer, release_year):
        super().__init__(name, genre, tempo, singer, release_year)
        self._similarity_score = list()
        self._set_of_song_names_with_scores = set()

    def add_similarity_score(self, score: float, song_name: str):
        self._similarity_score.append((score, song_name))
        self._set_of_song_names_with_scores.add(song_name)
        self._similarity_score = sorted(self._similarity_score, reverse=True)

    def check_similarity_score_present(self, song_name):
        return song_name in self._set_of_song_names_with_scores

    def get_similarity_scores(self):
        return self._similarity_score

    @staticmethod
    def build_similarity_index_matrix(metadata_list: list):
        no_of_songs = len(metadata_list)
        for i in range(no_of_songs):
            for j in range(no_of_songs):
                song_a = metadata_list[i]
                song_b = metadata_list[j]
                if i == j or song_a.check_similarity_score_present(song_b.get_name()) \
                        or song_b.check_similarity_score_present(song_a.get_name()):
                    continue
                else:
                    matching_attributes = 0
                    total_attributes = 0
                    song_b_dict = dict()
                    for attribute, value in song_b:
                        song_b_dict[attribute] = value
                    for attribute, value in song_a:
                        if value and song_b_dict[attribute] and value == song_b_dict[attribute]:
                            matching_attributes += 1
                        total_attributes += 1
                    similarity_score = matching_attributes / total_attributes
                    song_a.add_similarity_score(similarity_score, song_b.get_name())
                    song_b.add_similarity_score(similarity_score, song_a.get_name())


class RecommendationSystem:
    __metaclass__ = SingletonABCMeta

    @abstractmethod
    def recommend(self, song_name, exclude: set, top: int):
        pass


class Event(list):
    def __call__(self, *args, **kwargs):
        for item in self:
            item(*args, **kwargs)


class Library:
    def __init__(self, metadata_file_path):
        self._seed_file_path = metadata_file_path
        self._songs = self.__load_song_metadata()
        self.new_song_added = Event()

    def add_song(self, song: Song):
        self._songs.append(song)
        global song_names
        song_names.add(song.get_name())
        self.new_song_added(song)

    def __load_song_metadata(self):
        metadata_list = list()
        with open(self._seed_file_path, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            column_len = None
            for i, row in enumerate(reader):
                if i == 0:
                    column_len = len(row)
                else:
                    if len(row) != column_len:
                        raise Exception("Invalid columns in csv")
                    else:
                        metadata_list.append(
                            Song(row[0], row[1], row[2], row[3], row[4]))
        return metadata_list


def _alert_on_new_song_add(song):
    print(f'new song introduced in library {song}')
    global similarity_based_songs_metadata
    similarity_based_songs_metadata.append(SimilarityIndexBasedSongRecommendation(song.get_name(), song.get_genre(),
                                                                                  song.get_tempo(), song.get_singer(),
                                                                                  song.get_release_year()))
    SimilarityIndexBasedSongRecommendation.build_similarity_index_matrix(similarity_based_songs_metadata)


def _build_similarity_scores():
    global similarity_based_songs_metadata
    SimilarityIndexBasedSongRecommendation.build_similarity_index_matrix(similarity_based_songs_metadata)


class SimilarityBasedRecommendationSystem(RecommendationSystem):

    def __init__(self, metadata_file_path, songs_library: Library):
        global similarity_based_songs_metadata
        self._seed_file_path = metadata_file_path
        similarity_based_songs_metadata = self.__load_song_metadata()
        _build_similarity_scores()
        songs_library.new_song_added.append(_alert_on_new_song_add)

    def __load_song_metadata(self):
        metadata_list = list()
        with open(self._seed_file_path, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=',')
            column_len = None
            for i, row in enumerate(reader):
                if i == 0:
                    column_len = len(row)
                else:
                    if len(row) != column_len:
                        raise Exception("Invalid columns in csv")
                    else:
                        metadata_list.append(
                            SimilarityIndexBasedSongRecommendation(row[0], row[1], row[2], row[3], row[4]))
        return metadata_list

    def recommend(self, song_name, exclude, top=3):
        global similarity_based_songs_metadata
        result = list()
        for song in similarity_based_songs_metadata:
            if song_name == song.get_name():
                scores = song.get_similarity_scores()
                print(f'recommendation {scores} for {song_name}')
                for score, element in scores:
                    if element in exclude:
                        continue
                    else:
                        result.append(element)
                if top < len(result):
                    return result[0:top]
                else:
                    return result
        return result


class User:
    def __init__(self, name):
        self._name = name
        self._friends = set()
        self._playlist = dict()

    def get_name(self):
        return self._name

    def add_friend(self, name):
        if name in self._friends:
            raise Exception(f'Friend with name {name} already in friend list')
        self._friends.add(name)

    def remove_friend(self, name):
        if name in self._friends:
            self._friends.remove(name)
            return
        else:
            raise Exception(f'Friend with name {name} not found in friend list')

    def create_playlist(self, name, song_names: list):
        if name in self._playlist:
            raise Exception(f'create playlist with unique name, name already present: {name}')
        else:
            if song_names and len(song_names) != 0:
                self._playlist[name] = song_names
            else:
                self._playlist[name] = list()

    def delete_playlist(self, name):
        if name in self._playlist:
            del self._playlist[name]
        else:
            raise Exception(f'No playlist found with name: {name}')

    def add_song_to_playlist(self, playlist_name, song_name):
        global song_names
        if playlist_name in self._playlist and song_name in song_names:
            # adding same song again and again to playlist is allowed
            self._playlist[playlist_name].append(song_name)

    def get_unique_songs_from_playlists(self):
        unique_song_names = set()
        for playlist in self._playlist:
            song_names_in_playlist = self._playlist[playlist]
            for song_name in song_names_in_playlist:
                unique_song_names.add(song_name)
        return unique_song_names


class System:
    def __init__(self):
        self._users = list()

    def register_user(self, user: User):
        name = user.get_name()
        if not self.find_by_user_name(name):
            self._users.append(user)
            return
        else:
            raise Exception(f'User with name {name} already present in system')

    def find_by_user_name(self, name):
        for user in self._users:
            if user.get_name() == name:
                return user
        return None


if __name__ == '__main__':
    seed_file = '/Users/shivamsaxena/PycharmProjects/Interviews/music_recommendation/songs_metadata.csv'

    library = Library(seed_file)
    recommendation_system = SimilarityBasedRecommendationSystem(seed_file, library)

    u1 = User('Shivam')
    u2 = User('Saxena')
    system = System()
    system.register_user(u1)
    system.register_user(u2)
    u1.add_friend(u2.get_name())
    u2.add_friend(u1.get_name())
    u1.create_playlist('playlist1', ['ABC', 'HELLO'])
    u1.create_playlist('playlist2', ['ABC', 'WORLD'])
    u1_songs = u1.get_unique_songs_from_playlists()
    print(f'unique songs for {u1.get_name()}: {u1_songs}')
    u1_last_played_song = 'ABC'
    print("recommendations for user 1", recommendation_system.recommend(u1_last_played_song, u1_songs, 5))

    library.add_song(Song('LKO', 'A', 'SLOW', 'A', '2021'))
    print("recommendations for user 1", recommendation_system.recommend(u1_last_played_song, u1_songs, 5))

    # output
    '''
    unique songs for Shivam: {'ABC', 'HELLO', 'WORLD'}
    recommendation [(0.75, 'DEF'), (0.5, 'TEST'), (0.25, 'WORLD'), (0.25, 'OMEGA'), (0.25, 'HELLO'), (0.25, 'ALPHA'), (0.0, 'GH'), (0.0, 'GAMMA')] for ABC
    recommendations for user 1 ['DEF', 'TEST', 'OMEGA', 'ALPHA', 'GH']
    new song introduced in library Song name: LKO, genre: A, tempo: SLOW, singer: A, release year: 2021
    recommendation [(1.0, 'LKO'), (0.75, 'DEF'), (0.5, 'TEST'), (0.25, 'WORLD'), (0.25, 'OMEGA'), (0.25, 'HELLO'), (0.25, 'ALPHA'), (0.0, 'GH'), (0.0, 'GAMMA')] for ABC
    recommendations for user 1 ['LKO', 'DEF', 'TEST', 'OMEGA', 'ALPHA']
    '''






