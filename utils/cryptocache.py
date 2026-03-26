import time


class KeyCache:
    _cache = {}
    _last_refresh = 0
    TTL = 86400  # 24h

    

    @classmethod
    def get_key(cls, crypto):
        now = time.time()

        # 🔁 rotation si TTL expiré
        if now - cls._last_refresh > cls.TTL:
            cls._cache = {}
            cls._last_refresh = now

        # 🔑 récupérer clé

        if cls._cache is not None and 'InsuranceSecurity' in cls._cache:
            print("Clé trouvée")
            return cls._cache['InsuranceSecurity']
        else:
            print("Clé non trouvée, on la crée")
            cls._cache['InsuranceSecurity'] = crypto.get_keyset()
            return cls._cache['InsuranceSecurity']
            