# 🌐 DNS Configuration for Parkon.app

## Where to Configure DNS:
Go to your domain registrar where you bought "parkon.app" (like GoDaddy, Namecheap, Cloudflare, etc.)

---

## 📋 DNS Records to Add:

### If using Emergent Platform:
```
Type    Name              Value                           TTL
A       parkon.app        [Emergent-provided-IP]         300
A       www               [Emergent-provided-IP]         300
CNAME   api               parkon.app                      300
```

### If using your own server:
```
Type    Name              Value                           TTL
A       parkon.app        YOUR_SERVER_IP                 300
A       www               YOUR_SERVER_IP                 300
A       api               YOUR_SERVER_IP                 300
```

### Example with Cloudflare:
```
Type    Name              Content                         Proxy Status
A       parkon.app        104.21.45.123                  Proxied
A       www               104.21.45.123                  Proxied
A       api               104.21.45.123                  Proxied
```

---

## 🔧 Step-by-Step Instructions:

### 1. Login to Domain Registrar
- Go to your domain provider's website
- Login to your account
- Find "DNS Management" or "DNS Settings"

### 2. Add DNS Records
- Click "Add Record" or "+"
- Select record type: **A** or **CNAME**
- Enter the name and value as shown above
- Set TTL to **300** (5 minutes)
- Save changes

### 3. Verify DNS Propagation
Use online tools to check:
- https://dnschecker.org/
- Enter: parkon.app
- Should show your server IP globally

---

## ⏱️ DNS Propagation Time:
- **Cloudflare**: 2-5 minutes
- **Other providers**: 15 minutes - 24 hours
- **Global propagation**: Up to 48 hours

---

## 🛡️ SSL Certificate Setup:

### Option 1: Let's Encrypt (Free)
```bash
sudo apt install certbot
sudo certbot --nginx -d parkon.app -d www.parkon.app -d api.parkon.app
```

### Option 2: Cloudflare (Free + Easy)
1. Transfer DNS to Cloudflare
2. Enable "Proxied" status
3. SSL automatically enabled

---

## 🧪 Testing Your Setup:

### Test Main Domain:
```bash
curl -I https://parkon.app
# Should return: HTTP/2 200
```

### Test API Subdomain:
```bash
curl -I https://api.parkon.app/api/health
# Should return: HTTP/2 200
```

### Test WWW Redirect:
```bash
curl -I https://www.parkon.app
# Should redirect to: https://parkon.app
```

---

## 🎯 Quick Deployment Checklist:

- [ ] DNS records added at registrar
- [ ] SSL certificate installed
- [ ] App deployed to server
- [ ] Database configured
- [ ] CORS settings updated
- [ ] Test all subdomains working

---

## 📞 Need Help?

**Common Issues:**
1. **DNS not propagating**: Wait 24 hours or use Cloudflare
2. **SSL errors**: Use Let's Encrypt or Cloudflare
3. **CORS errors**: Check backend .env CORS_ORIGINS
4. **504 errors**: Check backend server is running

**Contact Support:**
- Domain registrar support for DNS issues
- Hosting provider support for server issues
- Emergent support for platform-specific help

Ready to go live? 🚀