import os
import subprocess
import openai
from github import Github

# Подключаем ключи
openai.api_key = os.getenv("OPENAI_API_KEY")
gh_token = os.getenv("GITHUB_TOKEN")
repo_name = os.getenv("GITHUB_REPOSITORY")
pr_number = os.getenv("GITHUB_REF").split("/")[-1]

# Получаем список изменённых файлов
diff_output = subprocess.check_output(["git", "diff", "--name-only", "HEAD^"]).decode().splitlines()
changed_files = [f for f in diff_output if f.endswith((".py", ".js", ".ts", ".go"))]

# Читаем содержимое файлов
file_contents = {}
for f in changed_files:
    try:
        with open(f, "r", encoding="utf-8") as file:
            file_contents[f] = file.read()
    except:
        pass

# Формируем запрос в ChatGPT
messages = [
    {"role": "system", "content": "Ты опытный code reviewer. Указывай баги, улучшения и стиль. Пиши кратко и по делу."}
]

for fname, code in file_contents.items():
    messages.append({"role": "user", "content": f"Файл: {fname}\n\n{code}"})

resp = openai.ChatCompletion.create(
    model="gpt-4o-mini",
    messages=messages,
    max_tokens=800
)

review_text = resp.choices[0].message["content"]

# Публикуем комментарий в PR
g = Github(gh_token)
repo = g.get_repo(repo_name)
pr = repo.get_pull(int(pr_number))
pr.create_issue_comment(f"🤖 AI Review:\n\n{review_text}")



