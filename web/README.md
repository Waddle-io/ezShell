# ezShell : proxy serveur (M2)

Le CLI ne contient **aucune clé**. Il parle à cette API, qui appelle Groq avec la clé du serveur.

```
CLI ──HTTPS──▶  /api/v1/device/register   (jeton d'appareil anonyme)
CLI ──HTTPS──▶  /api/v1/ask               (Bearer <jeton>) ──▶ Groq (clé serveur)
CLI ──HTTPS──▶  /api/v1/me                (statut, requêtes restantes)
```

## Mise en route (≈ 15 min)

1. **Neon** : crée un projet, copie la chaîne de connexion **pooled** (host avec `-pooler`, `?sslmode=require`).
2. **Schéma** : `cd web && npm install && DATABASE_URL='…' npm run db:migrate` (idempotent).
3. **Vercel** : importe le dépôt, *Root Directory* = `web`. Variables d'environnement (voir `.env.example`) :
   `DATABASE_URL`, `GROQ_API_KEY`, `LLM_MODEL`, `TOKEN_PEPPER` (`openssl rand -hex 32`), puis les limites.
   Ne jamais préfixer par `NEXT_PUBLIC_`. Ne jamais commiter `.env.local`.
4. **Vérifier** :
   ```bash
   curl https://TON-DOMAINE/api/v1/health
   T=$(curl -s -X POST https://TON-DOMAINE/api/v1/device/register | jq -r .device_token)
   curl -s -X POST https://TON-DOMAINE/api/v1/ask -H "authorization: Bearer $T" -H 'content-type: application/json' \
     -d '{"mode":"translate","query":"liste les fichiers"}'
   ```
5. **CLI** : `export EZSH_API_URL=https://TON-DOMAINE` puis Alt+E. Pour distribuer : renseigner `DEFAULT_API_URL`
   dans `src/core/proxy_client.py`. `EZSH_DIRECT=1` force l'ancien mode (clé Groq locale).

## Garde-fous

| Sujet | Mécanisme |
|---|---|
| Clé Groq | Variable serveur uniquement ; absente du client, des logs et de la base |
| Jeton d'appareil | 32 octets aléatoires ; seul son HMAC-SHA256 (poivré) est stocké ; révocable (`devices.revoked_at`) |
| Quotas | Incrément SQL **atomique** sous plafond (jamais de dépassement, même en parallèle) ; remboursé si le modèle échoue |
| Limites | Rafale/minute, enregistrements/IP/heure, quota/jour (anonyme et compte), **plafond global/jour** |
| Coupe-circuit | `KILL_SWITCH=1` ou `INSERT INTO settings VALUES ('kill_switch','1')` : effet immédiat, sans redéploiement |
| Secrets | 2e passe de masquage côté serveur (le client n'est pas digne de confiance) |
| Données | Aucune requête, sortie d'erreur ni commande stockée : seulement des compteurs |
| Sorties du modèle | Schéma zod, ANSI/contrôles retirés, 1 nouvel essai puis 502 |

## Tests

`TEST_DATABASE_URL=postgresql://… npm test` (Postgres jetable requis) · `npm run typecheck` · `npm run build`.

## Suite (M3)

Connexion par flux d'appareil : tables `device_codes` et `devices.user_id` déjà prêtes ; fournisseur d'auth à choisir
(Stack Auth ou Auth.js). Un appareil lié à un `user_id` suit déjà la limite « compte gratuit ».
