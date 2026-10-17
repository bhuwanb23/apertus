"""
    sys.exit(main())
if __name__ == "__main__":
kh = knowledge_human_agreement()
    if kh["status"] != "complete":
        print(f"  NOTE: human verification of the knowledge key is "
              f"{kh['status']}. The report says so rather than "
              f"carrying a placeholder for it.")
    have = any(s["knowledge"].get(m, {}).get("paired") for m in models)
    return 0 if have else 1


if __name__ == "__main__":
    sys.exit(main())
