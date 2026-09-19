const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const express = require('express');

const lastMessageCache = {};

const client = new Client({
    authStrategy: new LocalAuth(),
    puppeteer: { args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-accelerated-2d-canvas', '--disable-gpu', '--disable-background-timer-throttling', 
            '--disable-backgrounding-occluded-windows', 
            '--disable-renderer-backgrounding'] }
});

client.on('qr', (qr) => {
    console.log('📱 SCAN THIS QR CODE');
    qrcode.generate(qr, { small: true });
});

client.on('ready', () => {
    console.log('✅ WhatsApp Bridge is ready & authenticated.');
});

client.on('message_create', async (msg) => {
    const text = msg.body;
    if (!text) return;

    const isIncoming = !msg.fromMe;
    
    // Allow Y, N, 2, and 3 to pass through if sent from the Bot phone
    const textLower = text.toLowerCase().trim();
    const isMenuOrQuickReply = msg.fromMe && (textLower === 'y' || textLower === 'n' || text === '2' || text === '3');
    const isAdminCommand = msg.fromMe && (text.startsWith('#') || isMenuOrQuickReply);
    
    const isSelfChat = msg.fromMe && msg.to === msg.from;

    if (!isIncoming && !isAdminCommand && !isSelfChat) return;

    // Prevent infinite loops from bot's own output
    if (msg.fromMe && (text.includes('✅') || text.includes('⏳') || text.includes('❌') || text.includes('🔔') || text.includes('🚫') || text.includes('📊') || text.includes('🎉'))) {
        return;
    }

    // Get real phone number
    const contact = await msg.getContact();
    const senderPhone = '+' + contact.number; 
    console.log(`📩 Processing message from ${senderPhone}: ${text}`);

    // Save message to RAM cache
    lastMessageCache[senderPhone] = msg;

    try {
        const INTERNAL_PORT = process.env.PORT || 7860;

        // Update the axios call to using the dynamic port
        const response = await axios.post(`http://127.0.0.1:${INTERNAL_PORT}/api/v1/whatsapp`, {
            sender_phone: senderPhone,
            message_body: text
        });

        const data = response.data;

        if (data.reply) {
            await msg.reply(data.reply);
        }

        // Notify user fallback
        if (data.notify_user && data.notify_message) {
            const cachedMsg = lastMessageCache[data.notify_user];
            if (cachedMsg) {
                await cachedMsg.reply(data.notify_message);
            } else {
                const cleanNumber = data.notify_user.replace(/[^0-9]/g, '');
                await client.sendMessage(`${cleanNumber}@c.us`, data.notify_message).catch(e => console.error(e));
            }
        }

        // Notify admin fallback
        if (data.notify_admin && data.notify_admin_message) {
            const cachedAdminMsg = lastMessageCache[data.notify_admin];
            if (cachedAdminMsg) {
                await cachedAdminMsg.reply(data.notify_admin_message);
            } else {
                const cleanAdminNumber = data.notify_admin.replace(/[^0-9]/g, '');
                await client.sendMessage(`${cleanAdminNumber}@c.us`, data.notify_admin_message).catch(e => console.error(e));
            }
        }
    } catch (error) {
        console.error('❌ Failed to reach Python server.', error.message);
    }
});

// 🔌 EXPRESS SERVER FOR BACKGROUND TASKS (Weekly Summaries)
const app = express();
app.use(express.json());

app.post('/api/send', async (req, res) => {
    const { phone_number, message } = req.body;
    try {
        const cleanNumber = phone_number.replace(/[^0-9]/g, '');

        if (lastMessageCache[phone_number]) {
            const chat = await lastMessageCache[phone_number].getChat();
            await chat.sendMessage(message);
            return res.status(200).send({ success: true, method: "cache" });
        }

        const contactId = await client.getNumberId(cleanNumber);
        if (contactId) {
            await client.sendMessage(contactId._serialized, message);
            return res.status(200).send({ success: true, method: "getNumberId" });
        } else {
            await client.sendMessage(`${cleanNumber}@c.us`, message);
            return res.status(200).send({ success: true, method: "fallback" });
        }
    } catch (error) {
        console.error(`❌ Push failed for ${phone_number}:`, error.message);
        res.status(500).send({ error: error.message });
    }
});

app.listen(3000, () => {
    console.log('🔌 Outbound Gateway listening on port 3000');
});

client.initialize();