// Phase 22 sample data: players, scenes, and the words for each player's state.
window.MR = (function () {
  const NAMES = {
    living: 'Living Room', kitchen: 'Kitchen', study: 'Study', office: 'Office', garage: 'Garage', bedroom: 'Bedroom',
    dining: 'Kitchen and Dining Room', landing: 'Upstairs Landing', guest: 'Guest Bedroom by the Garden', workshop: 'Workshop'
  };
  const SCREEN = { living: true, kitchen: false, study: true, office: true, garage: false, bedroom: true, dining: false, landing: true, guest: true, workshop: false };
  const SRC = { lms: 'Lyrion', spotify: 'Spotify', plexamp: 'Plexamp', bluetooth: 'Bluetooth' };
  const LIST = ['living', 'kitchen', 'study', 'office', 'garage', 'bedroom'];
  const base = () => ({
    living: { state: 'playing', src: 'lms', vol: 62 },
    kitchen: { state: 'playing', src: 'spotify', vol: 48 },
    study: { state: 'idle', vol: 35 },
    office: { state: 'playing', src: 'plexamp', vol: 40, other: 'office' },
    garage: { state: 'playing', src: 'plexamp', vol: 70, other: 'office' },
    bedroom: { state: 'off', vol: 30 },
    dining: { state: 'idle', vol: 55 }, landing: { state: 'idle', vol: 40 },
    guest: { state: 'idle', vol: 30, fixed: true }, workshop: { state: 'idle', vol: 72 }
  });
  const grp = (lead, members, x) => Object.assign({ lead, members, joining: [], silent: false }, x || {});
  const G3 = () => grp('living', ['living', 'kitchen', 'study']);

  function scene(name) {
    const st = base();
    let g = null, me = 'living', list = LIST.slice();
    switch (name) {
      case 'joining': g = grp('living', ['living', 'kitchen', 'study'], { joining: ['study'] }); break;
      case 'leader': case 'undo': case 'vol': g = G3(); break;
      case 'fixed': g = G3(); st.study.fixed = true; break;
      case 'member': g = G3(); me = 'kitchen'; break;
      case 'nomark': g = G3(); me = 'kitchen'; break;
      case 'gone': g = grp('living', ['living', 'kitchen', 'study'], { silent: true }); st.living.state = 'off'; me = 'kitchen'; break;
      case 'left': g = grp('living', ['living', 'study']); st.kitchen = { state: 'idle', vol: 48 }; me = 'kitchen'; break;
      case 'undone': st.kitchen = { state: 'idle', vol: 48 }; break;
      case 'spotify': g = grp('kitchen', ['kitchen', 'living', 'study']); st.kitchen.src = 'spotify'; break;
      case 'two': g = grp('living', ['living', 'kitchen']); break;
      case 'five':
        list = ['living', 'dining', 'landing', 'study', 'guest', 'workshop', 'office', 'garage', 'bedroom'];
        g = grp('living', ['living', 'dining', 'landing', 'study', 'guest', 'workshop']); break;
    }
    if (g) g.members.forEach(k => { if (k !== g.lead && st[k].state !== 'off') st[k].state = 'group'; });
    return { me, g, st, list };
  }

  const name = k => NAMES[k] || k;
  const join = arr => arr.length < 2 ? arr.join('') : arr.slice(0, -1).join(', ') + ' and ' + arr[arr.length - 1];
  const srcOf = (sc) => { const g = sc.g; const k = g ? g.lead : sc.me; return (sc.st[k] && sc.st[k].src) || 'lms'; };

  // "with Kitchen, Study" for the mark; past two names the rest is a count.
  function withText(sc, viewer) {
    if (!sc.g) return ['', ''];
    const others = sc.g.members.filter(k => k !== viewer).map(name);
    if (others.length <= 2) return ['with ' + others.join(', '), ''];
    return ['with ' + others.slice(0, 2).join(', '), ' + ' + (others.length - 2)];
  }

  function rowStatus(sc, k) {
    const s = sc.st[k] || {}, g = sc.g;
    const inG = g && g.members.includes(k);
    if (s.state === 'off') return inG ? 'Off · was leading the group' : 'Not reachable';
    if (inG) {
      if (g.joining.includes(k)) return 'Joining · catching up';
      if (k === g.lead) return 'Playing · ' + SRC[s.src || 'lms'];
      return g.silent ? 'In this group · silent' : 'In this group';
    }
    if (s.other) {
      const mates = Object.keys(sc.st).filter(x => x !== k && sc.st[x].other === s.other && sc.list.includes(x)).map(name);
      return 'In a group with ' + join(mates) + ' · ' + SRC[s.src];
    }
    if (s.state === 'playing') return 'Playing · ' + SRC[s.src];
    if (s.state === 'paused') return 'Paused · ' + SRC[s.src];
    return 'Idle';
  }

  // mutations, on a copy
  const clone = sc => JSON.parse(JSON.stringify(sc));
  function joinTo(sc, k, viewer) {
    sc = clone(sc);
    const st = sc.st[k];
    if (st.other) { const o = st.other; delete st.other; const rest = Object.keys(sc.st).filter(x => sc.st[x].other === o); if (rest.length === 1) delete sc.st[rest[0]].other; }
    if (!sc.g) sc.g = grp(viewer, [viewer]);
    if (!sc.g.members.includes(k)) sc.g.members.push(k);
    sc.g.joining = sc.g.joining.filter(x => x !== k).concat([k]);
    st.state = 'group';
    return sc;
  }
  function settle(sc, k) { sc = clone(sc); if (sc.g) sc.g.joining = sc.g.joining.filter(x => x !== k); return sc; }
  function removeFrom(sc, k) {
    sc = clone(sc);
    if (!sc.g) return sc;
    sc.g.members = sc.g.members.filter(x => x !== k);
    sc.g.joining = sc.g.joining.filter(x => x !== k);
    if (sc.st[k].state !== 'off') sc.st[k].state = 'idle';
    if (sc.g.members.length < 2) { sc.g = null; }
    return sc;
  }
  function undo(sc) {
    sc = clone(sc);
    if (!sc.g) return sc;
    sc.g.members.forEach(k => { if (k !== sc.g.lead && sc.st[k].state !== 'off') sc.st[k].state = 'idle'; });
    sc.g = null;
    return sc;
  }

  return { NAMES, SCREEN, SRC, scene, name, join, withText, rowStatus, srcOf, joinTo, settle, removeFrom, undo, clone };
})();
