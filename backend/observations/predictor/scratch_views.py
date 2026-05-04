
@require_http_methods(["GET"])
def get_inat_photos(request):
    try:
        raw = request.GET.get('obs_ids', '').strip()
        if not raw:
            return JsonResponse({'photos': {}})
        obs_ids = [o.strip() for o in raw.split(',') if o.strip().isdigit()][:40]
        results, to_fetch = {}, []
        with _inat_photo_lock:
            for oid in obs_ids:
                if oid in _inat_photo_cache: results[oid] = _inat_photo_cache[oid]
                else: to_fetch.append(oid)
        def _fetch(obs_id):
            try:
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=12) as resp:
                    data = json.loads(resp.read().decode())
                photos = data.get('results', [{}])[0].get('photos', [])
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    return obs_id, url if url else None
            except Exception: pass
            return obs_id, None
        if to_fetch:
            with ThreadPoolExecutor(max_workers=12) as ex:
                for oid, url in [f.result() for f in as_completed({ex.submit(_fetch, o): o for o in to_fetch})]:
                    results[oid] = url
                    with _inat_photo_lock: _inat_photo_cache[oid] = url
        return JsonResponse({'photos': results})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_http_methods(["GET"])
def get_cluster_photos(request):
    """API: Get a collection of photos for a specific cluster."""
    try:
        ds = request.GET.get('dataset', 'animals').strip().lower()
        if ds not in ('animals', 'birds', 'insects'): ds = 'animals'
        n = max(3, min(20, int(request.GET.get('clusters', 8))))
        cid = int(request.GET.get('cluster_id', 0))
        
        df = _get_labeled_df(n, ds)
        if df is None:
            return JsonResponse({'photos': []})
            
        cdf = df[df['cluster'] == cid]
        if cdf.empty:
            return JsonResponse({'photos': []})
            
        # Extract iNat observation IDs
        obs_ids = []
        for oid in cdf['occurrenceID'].dropna():
            m = re.search(r'/observations/(\d+)', str(oid))
            if m:
                obs_ids.append(m.group(1))
        
        # Deduplicate and limit
        obs_ids = list(dict.fromkeys(obs_ids))[:40]
        
        results = []
        def _fetch(obs_id):
            try:
                req = Request(f'https://api.inaturalist.org/v1/observations/{obs_id}?fields=photos,taxon',
                               headers={'User-Agent': 'KoynaWildlifeApp/1.0'})
                with urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                res = data.get('results', [{}])[0]
                photos = res.get('photos', [])
                taxon = res.get('taxon', {})
                if photos:
                    url = (photos[0].get('url') or '').replace('/square.', '/medium.')
                    return {
                        'url': url,
                        'obs_id': obs_id,
                        'species': taxon.get('name', 'Unknown'),
                        'common_name': taxon.get('preferred_common_name', '')
                    }
            except Exception: pass
            return None

        if obs_ids:
            with ThreadPoolExecutor(max_workers=10) as ex:
                futures = {ex.submit(_fetch, o): o for o in obs_ids}
                for f in as_completed(futures):
                    res = f.result()
                    if res: results.append(res)
        
        return JsonResponse({'photos': results, 'count': len(results)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
