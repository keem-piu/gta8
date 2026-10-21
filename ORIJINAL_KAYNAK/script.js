const STATIC_STREAMERS = [
    "keempiu", "asepos", "limonvari", "x4te", "egemenfx", "chavohaze", "diorr35", "justwicky", "canarkhu", 
    "thekolpa", "aka", "gogo", "fjorgyn", "diana0035", "cjayhq", "dex0f", "liyantl", 
    "chicossberg", "rayz", "katasayf", "repkk", "pennia", "flavorr", "adamimlew", "rod4n", 
    "tacocan", "atillaberk", "burakg", "eduskaa", "qafsiiel", "fiorevelenoso", "timuty", 
    "quello00", "cero31", "zibrall", "ogibkg", "wasg0d", "gitartist", "liftof", "ertinayy", 
    "hakki34", "emrelax", "pumii", "egg4x", "bfly0", "liadona", "lmunchies", "odisnos", 
    "neocastro", "sapientum", "kamls", "rivxm0", "nadozp", "thxgqd", "anosx", "loudone", 
    "atapoze", "dexzyn", "ardafx", "bedo447", "icastra", "herayoo", "aqerion", "darkclef", 
    "flokzz", "hakanefe", "yonzef", "pyrox", "rrelia", "akaburaq", "costaan", "requsavage", 
    "reveneant", "owll6", "endeavorty", "prisioner", "frexrd", "elworry", "enzoomb", "gokhanhkn", 
    "armis618", "anshi666", "canerzodiac", "turkishtaco", "sweetycadi", "whatthemilqa", 
    "sakuraipek", "parlochef", "mralpkaan", "ammoarmen", "orumcekenver", "beratarsllan", 
    "orhunpaso", "mordredsly", "hudsoonn", "cagatayk", "phriksos"
];

let STREAMER_STATS = {};
const SPONSORED_STREAMER = "keempiu";
const updateIntervals = {};

function formatNumber(num) {
    if (!num) return "0";
    return num >= 1000 ? (num/1000).toFixed(1) + 'K' : num.toString();
}

function formatDate(dateString) {
    if (!dateString || dateString === "Hiç yayın yapmadı") return "Hiç yayın yapmadı";
    try {
        // Hem ISO hem de boşluklu tarihleri destekle
        const date = new Date(dateString.includes('T') ? dateString : dateString.replace(' ', 'T') + 'Z');
        if (isNaN(date.getTime())) return "Hiç yayın yapmadı";
        const diffMs = Date.now() - date.getTime();
        const diffMinutes = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        if (diffHours < 1) {
            return `${diffMinutes} dakika önce`;
        } else if (diffHours < 24) {
            return `${diffHours} saat önce`;
        } else {
            const diffDays = Math.floor(diffHours / 24);
            return `${diffDays} gün önce`;
        }
    } catch (e) {
        console.error("Tarih formatlama hatası:", e);
        return "Hiç yayın yapmadı";
    }
}

function formatDuration(startDate) {
    if (!startDate) return "0sn";
    
    try {
        const now = new Date();
        const start = new Date(startDate);
        
        if (isNaN(start.getTime())) {
            console.error("Geçersiz başlangıç tarihi:", startDate);
            return "0sn";
        }
        
        const diffSeconds = Math.floor((now - start) / 1000);
        
        if (diffSeconds < 0) return "0sn";

        const hours = Math.floor(diffSeconds / 3600);
        const minutes = Math.floor((diffSeconds % 3600) / 60);
        const seconds = diffSeconds % 60;

        const parts = [];
        if (hours > 0) parts.push(`${hours}sa`);
        if (minutes > 0 || hours > 0) parts.push(`${minutes}dk`);
        parts.push(`${seconds}sn`);

        return parts.join(" ");
    } catch (e) {
        console.error("Süre hesaplama hatası:", e);
        return "0sn";
    }
}

async function getProfilePicture(username) {
    const sizes = {
        small: `https://images.kick.com/channels/${username}/profile_small`,
        medium: `https://images.kick.com/channels/${username}/profile_medium`,
        large: `https://images.kick.com/channels/${username}/profile_large`
    };
    
    async function checkImage(url) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => resolve(url);
            img.onerror = () => resolve(null);
            img.src = url;
        });
    }
    
    const validUrl = await checkImage(sizes.small) || 
                    await checkImage(sizes.medium) || 
                    await checkImage(sizes.large);
    
    return validUrl || `https://via.placeholder.com/100/1a1a24/00ff00?text=${username.slice(0, 2).toUpperCase()}`;
}

async function fetchStreamerData(username) {
    try {
        // Profil ve canlı yayın verisini çek
        const [profileData, streamData] = await Promise.all([
            fetch(`https://kick.com/api/v2/channels/${username}`).then(res => res.json()),
            fetch(`https://kick.com/api/v2/channels/${username}/livestream`).then(res => res.json())
        ]);

        const profilePic = await getProfilePicture(username);

        let lastStream = profileData.last_live_at || null;

        // Eğer canlı değilse, son VOD tarihini dene
        if (!streamData?.is_live) {
            try {
                const vodRes = await fetch(`https://kick.com/api/v2/channels/${username}/videos?limit=1`);
                if (vodRes.ok) {
                    const vodData = await vodRes.json();
                    if (vodData.data && vodData.data.length > 0) {
                        lastStream = vodData.data[0].created_at;
                    } else if (profileData.last_live_at) {
                        lastStream = profileData.last_live_at;
                    } else {
                        lastStream = "Hiç yayın yapmadı";
                    }
                }
            } catch (vodErr) {
                console.error(`${username} VOD bilgisi alınamadı:`, vodErr);
                if (profileData.last_live_at) {
                    lastStream = profileData.last_live_at;
                } else {
                    lastStream = "Hiç yayın yapmadı";
                }
            }
        }

        return {
            username: username,
            isLive: streamData?.is_live || false,
            viewers: streamData?.viewer_count || 0,
            followers: formatNumber(profileData.followers_count || 0),
            lastStream: lastStream ? formatDate(lastStream) : "Hiç yayın yapmadı",
            title: streamData?.session_title || `${username} Kanalı`,
            thumbnail: streamData?.thumbnail?.url || null,
            startTime: streamData?.created_at || null,
            category: streamData?.categories?.[0]?.name || "GTA",
            profilePic: profilePic
        };
    } catch (error) {
        console.error(`${username} veri alım hatası:`, error);
        return {
            username: username,
            isLive: false,
            viewers: 0,
            followers: "0",
            lastStream: "Bilinmiyor",
            title: `${username} Kanalı`,
            thumbnail: null,
            startTime: null,
            category: "GTA",
            profilePic: await getProfilePicture(username)
        };
    }
}

async function fetchStreamerStats() {
    const stats = {};
    try {
        const requests = STATIC_STREAMERS.map(username => 
            fetchStreamerData(username).catch(e => {
                console.error(`${username} veri alınamadı:`, e);
                return {
                    username: username,
                    isLive: false,
                    viewers: 0,
                    followers: "0",
                    lastStream: "Bilinmiyor",
                    title: `${username} Kanalı`,
                    thumbnail: null,
                    startTime: null,
                    category: "GTA",
                    profilePic: `https://via.placeholder.com/100/1a1a24/00ff00?text=${username.slice(0, 2).toUpperCase()}`
                };
            })
        );
        
        const results = await Promise.all(requests);
        
        results.forEach(data => {
            stats[data.username] = data;
        });

        STREAMER_STATS = stats;
        return results;
    } catch (error) {
        console.error('Streamer istatistikleri alınamadı:', error);
        throw error;
    }
}

function updateDurationForCard(card, startTime) {
    if (!card || !startTime) return;
    const durationElement = card.querySelector('.live-duration');
    if (durationElement) {
        const duration = formatDuration(startTime);
        durationElement.textContent = `(${duration})`;
    }
}

function renderStreamers(streamersData) {
    const streamerList = document.getElementById('streamer-list');
    streamerList.innerHTML = '';

    Object.values(updateIntervals).forEach(interval => clearInterval(interval));
    Object.keys(updateIntervals).forEach(key => delete updateIntervals[key]);

    streamersData.forEach(data => {
        const isSponsored = data.username === SPONSORED_STREAMER;
        const isLive = data.isLive;
        const startTime = data.startTime;

        const streamerCard = document.createElement('div');
        streamerCard.className = 'streamer-card';
        streamerCard.dataset.username = data.username;
        if (isLive && startTime) {
            streamerCard.dataset.startTime = startTime;
        }

        const mediaContent = `
            <div class="streamer-media">
                ${isLive ?
                    `<iframe src="https://player.kick.com/${data.username}"
                                    class="streamer-iframe"
                                    height="180"
                                    frameborder="0"
                                    scrolling="no"
                                    allowfullscreen="true"></iframe>
                                <div class="live-badge">CANLI</div>` :
                    `<div class="offline-placeholder">
                        <img src="${data.profilePic}" alt="${data.username}" class="profile-image" onerror="this.src='https://via.placeholder.com/100/1a1a24/00ff00?text=${data.username.slice(0, 2).toUpperCase()}'">
                        <div class="offline-status">ÇEVRİMDIŞI</div>
                    </div>`}
                ${isSponsored ? '<div class="sponsored-badge">SPONSOR</div>' : ''}
            </div>
        `;

        const metaContent = `
            <div class="streamer-meta">
                <a href="https://kick.com/${data.username}" class="watch-button" target="_blank">
                    ${isLive ? 'İZLE' : 'KANAL'}
                </a>
                ${isLive ? `
                    <div class="viewer-count">
                        <span class="viewer-icon"></span>
                        ${formatNumber(data.viewers)}
                    </div>
                    ${startTime ? `<div class="live-duration">${formatDuration(startTime)}</div>` : ''}
                    <div class="streamer-category">${data.category}</div>
                ` : ''}
            </div>
        `;

        streamerCard.innerHTML = `
            ${mediaContent}
            <div class="streamer-info">
                <div class="streamer-name">${data.username}</div>
                <div class="streamer-title">${data.title}</div>
                ${metaContent}
                <div class="streamer-stats">
                    <div>${data.followers} takipçi</div>
                    <div class="streamer-last-stream">${isLive ? "Şu anda yayında" : `Son yayın: ${data.lastStream}`}</div>
                </div>
            </div>
        `;

        streamerList.appendChild(streamerCard);

        if (isLive && startTime) {
            updateDurationForCard(streamerCard, startTime);
            
            updateIntervals[data.username] = setInterval(() => {
                if (streamerCard.isConnected) {
                    updateDurationForCard(streamerCard, startTime);
                } else {
                    clearInterval(updateIntervals[data.username]);
                    delete updateIntervals[data.username];
                }
            }, 1000);
        }
    });
}

async function fetchStreamers() {
    const loadingElement = document.getElementById('loading');
    const errorElement = document.getElementById('error-message');
    const streamerList = document.getElementById('streamer-list');
    
    loadingElement.style.display = 'block';
    errorElement.style.display = 'none';
    streamerList.innerHTML = '';
    errorElement.textContent = '';

    try {
        const streamersData = await fetchStreamerStats();
        if (streamersData.length === 0) {
            throw new Error('Hiç yayıncı verisi alınamadı');
        }
        
        const sortedStreamers = streamersData.sort((a, b) => {
            if (a.isLive && !b.isLive) return -1;
            if (!a.isLive && b.isLive) return 1;
            return b.viewers - a.viewers;
        });
        
        renderStreamers(sortedStreamers);
        updateTime();
    } catch (error) {
        console.error('Hata:', error);
        showError(`Yayınlar yüklenirken bir hata oluştu: ${error.message}`);
    } finally {
        loadingElement.style.display = 'none';
    }
}

function showError(message) {
    const errorElement = document.getElementById('error-message');
    errorElement.textContent = message;
    errorElement.style.display = 'block';
}

function updateTime() {
    const now = new Date();
    document.getElementById('update-time').textContent =
        `${now.toLocaleDateString()} ${now.toLocaleTimeString()}`;
}

document.addEventListener('DOMContentLoaded', function() {
    fetchStreamers();
    setInterval(fetchStreamers, 300000); // 5 dakikada bir güncelle
});

async function getKickStreamerAllData(username) {
    // Profil, canlı yayın ve VOD verilerini çek
    const [profileRes, liveRes, vodRes] = await Promise.all([
        fetch(`https://kick.com/api/v2/channels/${username}`),
        fetch(`https://kick.com/api/v2/channels/${username}/livestream`),
        fetch(`https://kick.com/api/v2/channels/${username}/videos?limit=1`)
    ]);
    const profile = await profileRes.json();
    const live = await liveRes.json();
    const vods = await vodRes.json();

    // Son yayın tarihi
    let lastStream = profile.last_live_at || null;
    if (!live.is_live && vods.data && vods.data.length > 0) {
        lastStream = vods.data[0].created_at;
    }
    if (!lastStream) lastStream = "Hiç yayın yapmadı";

    // Kart için örnek veri
    return {
        username: profile.username,
        displayName: profile.user?.username || profile.username,
        isLive: live.is_live || false,
        title: live.session_title || "",
        category: live.categories?.[0]?.name || "GTA",
        viewers: live.viewer_count || 0,
        followers: profile.followers_count || 0,
        lastStream: lastStream,
        profilePic: profile.user?.profile_pic || "",
        vodTitle: vods.data?.[0]?.title || "",
        vodUrl: vods.data?.[0]?.source || "",
        vodCreated: vods.data?.[0]?.created_at || ""
    };
}

// Basit örnek kullanım:
getKickStreamerAllData("asepos").then(console.log);
