import json
from scrapy import Spider, Request, FormRequest
from music.settings import DEFAULT_REQUEST_HEADERS
from music.items import MusicItem


class MusicSpider(Spider):
    name = "music"
    allowed_domains = ["163.com"]
    base_url = 'https://music.163.com'
    ids = ['1001', '1002', '1003', '2001', '2002', '2003', '6001', '6002', '6003', '7001', '7002', '7003', '4001',
           '4002', '4003']
    initials = [i for i in range(65, 91)] + [0]

    def start_requests(self):
        for id in self.ids:
            for initial in self.initials:
                url = '{url}/discover/artist/cat?id={id}&initial={initial}'.format(url=self.base_url, id=id,
                                                                                       initial=initial)
                yield Request(url, callback=self.parse_index)

    # 获得所有歌手的url
    def parse_index(self, response):
        # 网易云音乐的歌手页有两个组成部分，上方十个带头像的热门歌手和下方只显示姓名的普通歌手，原来的xpath选择器只能得到热门歌手id，现已修改
        for sel in response.xpath('//*[@id="m-artist-box"]/li/*'):
            artist = sel.re('href\=\"\/artist\?id\=[(0-9)]{4,9}')
            for artistid in artist:
                artist_url = self.base_url + '/artist' + '/album?' + artistid[14:]
                yield Request(artist_url, callback=self.parse_artist_pre)

    def parse_artist_pre(self, response):
        # 得到专辑页的翻页html elements列表
        artist_albums = response.xpath('//*[@class="u-page"]/a[@class="zpgi"]/@href').extract()
        # 若为空，说明只有一页，即套用原parse_artist方法的代码，注意callback=self.parse_album
        if artist_albums == []:
            albums = response.xpath('//*[@id="m-song-module"]/li/div/a[@class="msk"]/@href').extract()
            for album in albums:
                album_url = self.base_url + album
                yield Request(album_url, callback=self.parse_album)
        # 若不为空，即该歌手专辑存在分页，那么得到分页的url，注意callback=self.parse-artist
        else:
            for artist_album in artist_albums:
                artist_album_url = self.base_url + artist_album
                yield Request(artist_album_url, callback=self.parse_artist)

    # 获得所有歌手专辑的url
    def parse_artist(self, response):
        albums = response.xpath('//*[@id="m-song-module"]/li/div/a[@class="msk"]/@href').extract()
        for album in albums:
            album_url = self.base_url + album
            yield Request(album_url, callback=self.parse_album)

    # 获得所有专辑音乐的url
    def parse_album(self, response):
        musics = response.xpath('//ul[@class="f-hide"]/li/a/@href').extract()
        for music in musics:
            music_id = music[9:]
            music_url = self.base_url + music
            yield Request(music_url, meta={'id': music_id}, callback=self.parse_music)

    # 获取音乐信息
    def parse_music(self, response):
        music_id = response.meta['id']
        music = response.xpath('//div[@class="tit"]/em[@class="f-ff2"]/text()').extract_first()
        artist = response.xpath('//div[@class="cnt"]/p[1]/span/a/text()').extract_first()
        album = response.xpath('//div[@class="cnt"]/p[2]/a/text()').extract_first()
        data = {
            'csrf_token': '',
            'params': 'Ak2s0LoP1GRJYqE3XxJUZVYK9uPEXSTttmAS+8uVLnYRoUt/Xgqdrt/13nr6OYhi75QSTlQ9FcZaWElIwE+oz9qXAu87t2DHj6Auu+2yBJDr+arG+irBbjIvKJGfjgBac+kSm2ePwf4rfuHSKVgQu1cYMdqFVnB+ojBsWopHcexbvLylDIMPulPljAWK6MR8',
            'encSecKey': '8c85d1b6f53bfebaf5258d171f3526c06980cbcaf490d759eac82145ee27198297c152dd95e7ea0f08cfb7281588cdab305946e01b9d84f0b49700f9c2eb6eeced8624b16ce378bccd24341b1b5ad3d84ebd707dbbd18a4f01c2a007cd47de32f28ca395c9715afa134ed9ee321caa7f28ec82b94307d75144f6b5b134a9ce1a'
        }

        DEFAULT_REQUEST_HEADERS['Referer'] = self.base_url + '/playlist?id=' + str(music_id)
        music_comment = 'http://music.163.com/weapi/v1/resource/comments/R_SO_4_' + str(music_id)
        yield FormRequest(music_comment, meta={'id': music_id, 'music': music, 'artist': artist, 'album': album},
                          callback=self.parse_comment, formdata=data)

    # 获得所有音乐的热评数据
    def parse_comment(self, response):
        id = response.meta['id']
        music = response.meta['music']
        artist = response.meta['artist']
        album = response.meta['album']
        result = json.loads(response.text)
        comments = []
        if 'hotComments' in result.keys():
            for comment in result.get('hotComments'):
                hotcomment_author = comment['user']['nickname']
                hotcomment = comment['content']
                hotcomment_like = comment['likedCount']
                hotcomment_avatar = comment['user']['avatarUrl']
                data = {
                    'nickname': hotcomment_author,
                    'content': hotcomment,
                    'likedcount': hotcomment_like,
                    'avatarurl': hotcomment_avatar
                }
                comments.append(data)

        item = MusicItem()
        for field in item.fields:
            try:
                item[field] = eval(field)
            except:
                print('Field is not defined', field)
        yield item
