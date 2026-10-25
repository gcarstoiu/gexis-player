// gexis 13f — sample data and the shape/colour assignments for Lyrion's menus.
// Labels in MY_MUSIC, the app first levels and the tree are Lyrion's own (brief
// 13f, measured 2026-10-06). Artist, album, genre and track names are samples.
(function () {
  var T = { mint: '#7ed6bc', blue: '#9fb4e8', coral: '#f2a48f', amber: '#e0a758', lilac: '#c8a2d8', sky: '#8fc4d8', slate: '#b0bcc4', pink: '#e8a0b4', green: '#8fd9a8', ink: '#e9eef2' };

  // My Music, regrouped by what an entry opens. [label, glyph, tint, opens]
  var MY_MUSIC = [
    { group: 'Artists', ink: T.blue, items: [
      ['All Artists', 'Person', T.blue, 'artists'], ['Composers', 'Score', T.lilac, 'artists'],
      ['Popular Artists', 'Podium', T.amber, 'ranked'], ['New Artists', 'Spark', T.green, 'artists'],
      ['Recently Played Artists', 'Clock', T.sky, 'artists']] },
    { group: 'Albums', ink: T.mint, items: [
      ['Albums', 'Sleeve', T.mint, 'covers'], ['New Music', 'Stack', T.coral, 'covers'],
      ['Random Albums', 'Dice', T.pink, 'covers'], ['Popular Albums', 'Crown', T.amber, 'covers'],
      ['Recently Updated Albums', 'Refresh', T.sky, 'covers'], ['Compilations', 'Fan', T.blue, 'covers'],
      ['Works', 'Pillar', T.lilac, 'covers']] },
    { group: 'By category', ink: T.coral, items: [
      ['Genres', 'Tag', T.coral, 'genres'], ['Years', 'Calendar', T.amber, 'years'],
      ['Music Folder', 'Folder', T.mint, 'folder'], ['Disks and folders', 'Disk', T.slate, 'folder']] },
    { group: 'Tracks', ink: T.green, items: [
      ['Top Tracks', 'Up', T.green, 'tracks'], ['Flop Tracks', 'Down', T.slate, 'tracks']] },
    { group: 'More', ink: T.lilac, items: [
      ['Search', 'Search', T.ink, 'search'], ['Library Views', 'Layers', T.lilac, 'rows'],
      ['Remote Music Libraries', 'Servers', T.sky, 'rows']] }
  ];

  // An app level's entries get their shape from their label first, then from
  // Lyrion's hint, then Folder. One table for every app.
  var KEYWORDS = [
    [/search/i, 'Search', T.ink], [/purchase/i, 'Bag', T.blue], [/favou?rite/i, 'Heart', T.pink],
    [/^my playlists|^playlists/i, 'Lines', T.coral], [/playlists/i, 'Lines', T.sky],
    [/bestseller|popular|top /i, 'Crown', T.amber], [/new|what's new/i, 'Spark', T.green],
    [/press/i, 'Press', T.slate], [/selection|editor|pick/i, 'Star', T.lilac], [/genre|mood/i, 'Tag', T.mint],
    [/^home$/i, 'House', T.mint], [/album/i, 'Sleeve', T.mint], [/artist/i, 'Person', T.blue],
    [/podcast/i, 'Mic', T.lilac], [/alarm/i, 'Clock', T.amber], [/musical/i, 'Note', T.coral],
    [/natural/i, 'Leaf', T.green], [/effect/i, 'Spark', T.sky]
  ];
  var HINTS = { genre: ['Tag', T.coral], year: ['Calendar', T.amber], folder: ['Folder', T.mint], artist: ['Person', T.blue], album: ['Sleeve', T.mint], work: ['Pillar', T.lilac], app: ['Dots', T.lilac] };
  function shapeFor(label, hint) {
    for (var i = 0; i < KEYWORDS.length; i++) if (KEYWORDS[i][0].test(label || '')) return [KEYWORDS[i][1], KEYWORDS[i][2]];
    if (hint && HINTS[hint]) return HINTS[hint];
    return ['Folder', T.sky];
  }

  var APPS = [
    { name: 'Qobuz', sub: '10 entries', logo: null, letter: 'Q', first: ['Search', 'My Purchases', 'My Favourites', 'My Playlists', 'Qobuz Playlists', 'Bestsellers', 'New Releases', 'In the Press', 'Qobuz Selection', 'Genres'] },
    { name: 'Spotty', sub: 'Spotify', logo: 'icon-spotify.png', letter: 'S', first: ['Home', 'Search', "What's New", 'Top Tracks', 'Genres and Moods', 'Popular Playlists', 'Albums', 'Artists', 'Playlists', 'Podcasts'] },
    { name: 'YouTube', sub: '11 searches', logo: null, letter: 'Y' },
    { name: 'Radio Paradise', sub: '6 mixes · 2 streams', logo: null, letter: 'RP' },
    { name: 'Sounds & Effects', sub: '4 collections', logo: null, letter: 'S&E', first: ['Alarm Sounds', 'Musical Sounds', 'Natural Sounds', 'Sound Effects'] },
    { name: 'TIDAL', sub: 'Not signed in', logo: null, letter: 'T' }
  ];

  // YouTube: the five named in the brief, then sample labels for the other six.
  var YT_KINDS = ['Video', 'Music', 'Channel', 'Playlist', 'URL', 'Live', 'Video ID', 'Playlist ID', 'Channel ID', 'Recent searches', 'Region'];
  var YT_LISTS = ['Subscriptions', 'Recently played', 'Watch later'];
  var RP = { mixes: ['Main Mix', 'Mellow Mix', 'Rock Mix', 'Global Mix', 'Beyond', 'Serenity'], streams: ['Radio 2050', 'Paradise Lounge'], qualities: [['FLAC', 'lossless'], ['AAC 320', 'kbps'], ['AAC 128', 'kbps'], ['AAC 64', 'kbps']] };

  var ARTISTS_A = ['Aaliyah', 'ABBA', 'Abdullah Ibrahim', 'AC/DC', 'Adele', 'Air', 'Al Green', 'Alice Coltrane', 'Amadou & Mariam', 'Andra', 'Angèle', 'Anouar Brahem', 'Aphex Twin', 'Arca', 'Arvo Pärt', 'Astrud Gilberto', 'Aurora', 'Ayo'];
  var ARTISTS_B = ['Bach Collegium Japan', 'Badbadnotgood', 'Bebel Gilberto', 'Beirut', 'Bill Evans', 'Bime'];
  var RANKED = [['Gasca Zurli', 412], ['Andra', 287], ['Cleopatra Stratan', 203], ['Bime', 166], ['Alice Coltrane', 121], ['Bill Evans', 98], ['Air', 84], ['Anouar Brahem', 71], ['Arvo Pärt', 64], ['Beirut', 52], ['Aurora', 47], ['Adele', 40]];
  var GENRES = ['Acid Jazz', 'Afrobeat', 'Alternative', 'Ambient', 'Big Band', 'Blues', 'Bossa Nova', "Children's Music", 'Classical', 'Country', 'Dance', 'Disco', 'Dub', 'Electronic', 'Folk', 'Funk', 'Gospel', 'Hip-Hop'];
  var YEARS = { '2020s': [2026, 2025, 2024, 2023, 2022, 2021, 2020], '2010s': [2019, 2018, 2017, 2016, 2015, 2014, 2013, 2012, 2011, 2010], '2000s': [2009, 2008, 2007, 2006, 2005, 2004, 2003, 2002, 2001, 2000], '1990s': [1999, 1998, 1997, 1996, 1995, 1994, 1993, 1992, 1991, 1990], '1980s': [1989, 1987, 1986, 1984, 1983, 1981] };
  var ALBUMS = [['Atentiune, Acceleram!', 'Gasca Zurli'], ['Cantece Pentru Copii', 'Gasca Zurli'], ['Zurli Mania', 'Gasca Zurli'], ['La Plimbare', 'Cleopatra Stratan'], ['Vine Vine Primavara', 'Gasca Zurli'], ['Cantece Mici', 'Cantece Mici'], ['Bime Live', 'Bime'], ['Hai La Joc', 'Various Artists'], ['Neconditionat', 'Andra'], ['Night Bus Sessions', 'Bime'], ['Journey in Satchidananda', 'Alice Coltrane'], ['Moon Safari', 'Air'], ['Le Pas du Chat Noir', 'Anouar Brahem'], ['Tabula Rasa', 'Arvo Pärt'], ['Gulag Orkestar', 'Beirut'], ['Waltz for Debby', 'Bill Evans'], ['Andra Live', 'Andra'], ['Ghita', 'Cleopatra Stratan']];
  var TOP = [['Rempompi', 'Gasca Zurli – Atentiune, Acceleram!', 189], ['Trenulet', 'Gasca Zurli – Cantece Pentru Copii', 164], ['Inima Nu Vrea', 'Andra – Neconditionat', 140], ['Ghita', 'Cleopatra Stratan – Ghita', 122], ['Zurli Dance', 'Gasca Zurli – Zurli Mania', 117], ['Night Bus', 'Bime – Night Bus Sessions', 96], ['La Femme d\u2019Argent', 'Air – Moon Safari', 88], ['Cifrele', 'Gasca Zurli – Atentiune, Acceleram!', 81], ['Peace on Earth', 'Bill Evans – Waltz for Debby', 74]];
  var FLOP = [['Interlude (Reprise)', 'Various Artists – Hai La Joc'], ['Tuning', 'Bime – Bime Live'], ['Applause', 'Andra – Andra Live'], ['Hidden Track', 'Cantece Mici – Cantece Mici'], ['Count-in', 'Bime – Night Bus Sessions'], ['Outro', 'Gasca Zurli – Zurli Mania'], ['Silence', 'Arvo Pärt – Tabula Rasa'], ['Room Tone', 'Air – Moon Safari']];
  var QALBUM = { title: 'Atentiune, Acceleram!', artist: 'Gasca Zurli', year: '2026',
    tracks: [['Rempompi', '1:55'], ['Trenulet', '2:12'], ['Zurli Dance', '2:41'], ['Cifrele', '1:48'], ['Ursuletul', '2:07'], ['Alfabetul', '2:33'], ['La Gradinita', '1:59'], ['Noapte Buna', '3:04'], ['Vine Toamna', '2:22'], ['Hai Acasa', '2:51']],
    facts: [['Genre', 'Metal'], ['Release type', 'Album'], ['Duration', '0:46:05'], ['Tracks', '10'], ['Released', '10/02/2026']],
    links: [['Artist', 'Gasca Zurli'], ['Music label', 'Cat Music'], ['Credits', ''], ['Copyright', '']] };
  var FAVS = [['Radio Paradise – Main Mix', 'Station', 'station'], ['Moon Safari', 'Air', 'album'], ['Kids Road Trip', 'Playlist · 24 tracks', 'playlist'], ['Rempompi', 'Gasca Zurli – Atentiune, Acceleram!', 'track'], ['Evening', 'Folder · 6 items', 'folder'], ['Deutschlandfunk', 'Station', 'station'], ['Waltz for Debby', 'Bill Evans', 'album'], ['Tabula Rasa', 'Arvo Pärt', 'album']];

  window.LyrionData = { T: T, MY_MUSIC: MY_MUSIC, shapeFor: shapeFor, APPS: APPS, YT_KINDS: YT_KINDS, YT_LISTS: YT_LISTS, RP: RP, ARTISTS_A: ARTISTS_A, ARTISTS_B: ARTISTS_B, RANKED: RANKED, GENRES: GENRES, YEARS: YEARS, ALBUMS: ALBUMS, TOP: TOP, FLOP: FLOP, QALBUM: QALBUM, FAVS: FAVS };
})();
