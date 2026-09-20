const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, Browsers } = require('@whiskeysockets/baileys');
const pino = require('pino');
const express = require('express');
const axios = require('axios');
const qrcode = require('qrcode-terminal');

const INTERNAL_PORT = process.env.PORT || 7860;
const EXPRESS_PORT = process.env.BRIDGE_PORT || 3000;

const app = express();
app.use(express.json());

const lastMessageCache = {};
let sock;

async function connectToWhatsApp() {
    const { state, saveCreds } = await useMultiFileAuthState('baileys_auth_info');
    const version = [2, 3000, 1042626022];

    // 1. Initialize the socket first so sock.ev exists
    sock = makeWASocket({
        version,
        logger: pino({ level: 'silent' }),
        auth: state,
        browser: Browsers.ubuntu('Chrome'),
        generateHighQualityLinkPreview: true,
    });

    // 2. Save credentials
    sock.ev.on('creds.update', saveCreds);

    // 3. Connection & QR handler
    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log('\n📱 SCAN THIS QR CODE:');
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
            console.log(`⚠️ Connection closed (${statusCode}). Reconnecting: ${shouldReconnect}`);
            if (shouldReconnect) {
                setTimeout(connectToWhatsApp, 5000);
            }
        } else if (connection === 'open') {
            console.log('✅ Baileys WebSocket Bridge is ready & authenticated!');
        }
    });

    // 4. Message handler with filters & FastAPI dispatch
    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;
        const msg = messages[0];
        if (!msg.message) return;

        const text = msg.message?.conversation || msg.message?.extendedTextMessage?.text || '';
        if (!text) return;

        // Admin & quick-reply filter rules
        const textLower = text.toLowerCase().trim();
        const isIncoming = !msg.key.fromMe;
        const isMenuOrQuickReply = msg.key.fromMe && (textLower === 'y' || textLower === 'n' || text === '2' || text === '3');
        const isAdminCommand = msg.key.fromMe && (text.startsWith('#') || isMenuOrQuickReply);

        const botBaseJid = sock.user?.id ? sock.user.id.split(':')[0] : '';
        const isSelfChat = msg.key.fromMe && msg.key.remoteJid && msg.key.remoteJid.includes(botBaseJid);

        if (!isIncoming && !isAdminCommand && !isSelfChat) return;

        // Loop prevention against bot echo
        if (msg.key.fromMe && (text.includes('✅') || text.includes('⏳') || text.includes('❌') || text.includes('🔔') || text.includes('🚫') || text.includes('📊') || text.includes('🎉'))) {
            return;
        }

        // Extract clean phone number (handle LID / alt JID)
        let phoneJid = msg.key.remoteJid;
        const whatsappLid = '+' + phoneJid.split('@')[0];
        console.log("phone Jid :",phoneJid)
        console.log("whatsappLid 1",whatsappLid)
        if (msg.key.remoteJidAlt && msg.key.remoteJidAlt.includes('@s.whatsapp.net')) {
            phoneJid = msg.key.remoteJidAlt;
            console.log("phoneJid 2",phoneJid)

        }

        const senderPhone = '+' + phoneJid.split('@')[0];
        console.log(`📩 Processing message from ${senderPhone}: ${text}`);

        // Store message in cache for potential follow-up notifications
        lastMessageCache[senderPhone] = msg;

        try {
            const response = await axios.post(`http://127.0.0.1:${INTERNAL_PORT}/api/v1/whatsapp`, {
                sender_phone: whatsappLid,
                message_body: text
            });

            const data = response.data;

            // Direct reply to the incoming message
            if (data.reply) {
                await sock.sendMessage(msg.key.remoteJid, { text: data.reply }, { quoted: msg });
            }

            // User notification dispatch
            if (data.notify_user && data.notify_message) {
                const rawNumber = data.notify_user.replace(/[^0-9]/g, '');
                const cacheKey = '+' + rawNumber;
                const cachedMsg = lastMessageCache[cacheKey];

                if (cachedMsg) {
                    await sock.sendMessage(cachedMsg.key.remoteJid, { text: data.notify_message }, { quoted: cachedMsg });
                } else {
                    await sock.sendMessage(`${rawNumber}@s.whatsapp.net`, { text: data.notify_message });
                }
            }

            // Admin notification dispatch
            if (data.notify_admin && data.notify_admin_message) {
                const rawAdminNumber = data.notify_admin.replace(/[^0-9]/g, '');
                const cacheAdminKey = '+' + rawAdminNumber;
                const cachedAdminMsg = lastMessageCache[cacheAdminKey];

                if (cachedAdminMsg) {
                    await sock.sendMessage(cachedAdminMsg.key.remoteJid, { text: data.notify_admin_message }, { quoted: cachedAdminMsg });
                } else {
                    await sock.sendMessage(`${rawAdminNumber}@s.whatsapp.net`, { text: data.notify_admin_message });
                }
            }
        } catch (error) {
            console.error('❌ Failed to reach Python server:', error.message);
        }
    });
}

// Outbound Gateway for background tasks / cron alerts
app.post('/send', async (req, res) => {
    const { phone_number, message } = req.body;
    try {
        const cleanNumber = phone_number.replace(/[^0-9]/g, '');
        const jid = `${cleanNumber}@s.whatsapp.net`;
        await sock.sendMessage(jid, { text: message });
        res.status(200).send({ status: 'sent' });
    } catch (error) {
        console.error('❌ Error sending outbound message:', error.message);
        res.status(500).send({ error: 'Failed to send message' });
    }
});

app.listen(EXPRESS_PORT, () => {
    console.log(`🔌 Baileys Outbound Gateway listening on port ${EXPRESS_PORT}`);
    connectToWhatsApp();
});