#!/usr/bin/env python3
"""Sistem pakar sederhana: penyebab bacaan jarak sensor ultrasonik HC-SR04 salah atau tidak stabil.
Mesin inferensi: forward chaining (ditulis sendiri, tanpa library pakar).

Pemakaian:
  python sensor_pakar.py                      -> mode tanya-jawab (y/t)
  python sensor_pakar.py --ya "fakta1;fakta2" -> langsung beri fakta "ya"
  python sensor_pakar.py --uji kasus_uji.json -> jalankan kasus uji otomatis
"""
import argparse
import json
import sys


def muat_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def syarat_terpenuhi(aturan, memori):
    """mode 'dan' = semua syarat ada di memori, 'atau' = salah satu cukup."""
    if aturan["mode"] == "dan":
        return all(s in memori for s in aturan["jika"])
    return any(s in memori for s in aturan["jika"])


def fakta_dasar(kb):
    """Fakta yang tidak pernah menjadi hasil aturan (ditanyakan ke user)."""
    hasil_aturan = {r["maka"] for r in kb["aturan"]}
    urut = []
    for r in kb["aturan"]:
        for s in r["jika"]:
            if s not in hasil_aturan and s not in urut:
                urut.append(s)
    return urut


def forward_chaining(kb, fakta_awal):
    memori = set(fakta_awal)
    asal = {}  # fakta turunan -> aturan yang menghasilkannya
    log = []
    siklus = 0
    while True:
        cocok = [r for r in kb["aturan"]
                 if syarat_terpenuhi(r, memori) and r["maka"] not in memori]
        if not cocok:
            log.append(f"Siklus {siklus + 1}: tidak ada aturan baru, berhenti")
            break
        r = cocok[0]  # ambil aturan pertama
        siklus += 1
        memori.add(r["maka"])
        asal[r["maka"]] = r
        log.append(f"Siklus {siklus}: {r['id']} -> {r['maka']}")
    return memori, asal, log


def kesimpulan_akhir(kb, asal):
    """Fakta turunan yang tidak dipakai sebagai syarat aturan lain."""
    dipakai = {s for r in kb["aturan"] for s in r["jika"]}
    return [f for f in asal if f not in dipakai]


def jelaskan(fakta, asal, memori, tingkat=0, keluar=None):
    keluar = [] if keluar is None else keluar
    r = asal[fakta]
    dipakai = [s for s in r["jika"] if s in memori]
    keluar.append("  " * (tingkat + 1) +
                  f"{fakta}  <- {r['id']} ({', '.join(dipakai)}) [{r['sumber']}]")
    for s in dipakai:
        if s in asal:
            jelaskan(s, asal, memori, tingkat + 1, keluar)
    return keluar


def tanya_user(kb):
    print("Jawab y/t.")
    ya = []
    for i, f in enumerate(fakta_dasar(kb), 1):
        teks = kb["pertanyaan"].get(f, f"Apakah {f}?")
        while True:
            try:
                jawab = input(f"{i}. {teks} (y/t) > ").strip().lower()
            except EOFError:
                jawab = "t"
            if jawab in ("y", "t"):
                break
        if jawab == "y":
            ya.append(f)
    return ya


def jalankan(kb, ya, tampil=True):
    memori, asal, log = forward_chaining(kb, ya)
    akhir = kesimpulan_akhir(kb, asal)
    if tampil:
        print()
        print("Fakta awal:", ", ".join(ya) if ya else "(tidak ada)")
        print()
        for baris in log:
            print(baris)
        print()
        if not akhir:
            print("Kesimpulan: tidak ada kesimpulan dari fakta yang diberikan")
        else:
            for k in akhir:
                print("Kesimpulan:", k)
            print("Alasan:")
            for k in akhir:
                for baris in jelaskan(k, asal, memori):
                    print(baris)
        print()
        print("Catatan:", kb["batas"])
    return akhir


def jalankan_uji(kb, path):
    kasus = muat_json(path)
    gagal = 0
    for k in kasus:
        print("=" * 70)
        print(f"Kasus {k['no']}: {k['nama']}")
        akhir = jalankan(kb, k["ya"])
        ok = set(akhir) == set(k["diharapkan"])
        gagal += 0 if ok else 1
        print(f"\nHASIL UJI: {'LULUS' if ok else 'GAGAL'}")
    print("=" * 70)
    print(f"Ringkasan: {len(kasus) - gagal}/{len(kasus)} kasus lulus")
    return gagal


def main():
    p = argparse.ArgumentParser(description="Sistem pakar sensor ultrasonik HC-SR04 (forward chaining)")
    p.add_argument("--kb", default="kb_ultrasonik.json", help="file basis pengetahuan")
    p.add_argument("--ya", help="fakta 'ya' dipisah titik koma (tanpa tanya-jawab)")
    p.add_argument("--uji", help="file kasus uji JSON")
    a = p.parse_args()

    kb = muat_json(a.kb)
    if a.uji:
        sys.exit(1 if jalankan_uji(kb, a.uji) else 0)

    print(kb["judul"])
    if a.ya is not None:
        ya = [x.strip() for x in a.ya.split(";") if x.strip()]
        valid = set(fakta_dasar(kb))
        salah = [x for x in ya if x not in valid]
        if salah:
            sys.exit("Fakta tidak dikenal: " + ", ".join(salah))
    else:
        ya = tanya_user(kb)
    jalankan(kb, ya)


if __name__ == "__main__":
    main()
