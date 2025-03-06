import os
import json
import dotenv
import datetime
import random
import asyncio
import pandas as pd
import discord
from discord.ext import tasks
from discord import app_commands
import ui
import Score_Analysis as SA
import Score_Analysis_ui as SA_ui
import Arcaea_command
import ChatBot


#ユーザー登録変数の読み込み
dotenv.load_dotenv()
#アクセストークンを取得
TOKEN = os.environ["BOT_TOKEN"] # ["DEBUG_BOT_TOKEN"]
GPT_TOKEN = os.environ["CHAT_GPT_TOKEN"]
#接続に必要なオブジェクトを生成
client = discord.Client(intents=discord.Intents.all())
tree = app_commands.CommandTree(client)
chatgpt = ChatBot.Chat_GPT(GPT_TOKEN, os.environ["ARKY_PROMPT"])


@client.event
async def on_ready():
    """初回起動設定"""
    #各種IDを取得
    global Creater_DM, Creater_ID, Server_ID, BotRole_ID, Command_CH, Battle_CH, Arky_CH, Analysis_CH, Create_RoomID, Arcaea_Tier_URL
    Creater_ID = int(os.environ["CREATER_ID"]) #私のユーザーID
    Server_ID = int(os.environ["SERVER_ID"]) #「Arcaea Verse」のサーバーID
    BotRole_ID = int(os.environ["BOTROLE_ID"]) #サーバーでbotを使用する権限を管理するロールID
    Command_CH = int(os.environ["COMMAND_CH"]) #コマンドを入力するチャンネル
    Battle_CH = int(os.environ["BATTLE_CH"]) #ランダムバトルを行うチャンネル
    Arky_CH = int(os.environ["ARKY_CH"]) #Arkyちゃんのお部屋のID
    Analysis_CH = int(os.environ["ANALYSIS_CH"]) #スコア分析CH
    Create_RoomID = int(os.environ["CREATER_ROOM_ID"]) #開発チャンネルのID
    Arcaea_Tier_URL = os.environ["ARCAEATIER_URL"] #ティア表作成webサイトのURL

    #管理者のDMオブジェクトを作成
    Creater = await client.fetch_user(Creater_ID)
    Creater_DM = await Creater.create_dm()

    #コマンドの更新
    await tree.sync()
    #viwe = await tree.fetch_commands() #登録されてるコマンドを表示するやつ
    #print(viwe)

    #ログイン通知
    await Creater_DM.send("起動したよ")
    #対戦ボタン表示
    await show_button(Battle_CH, "BattleSelect_message_id")
    await show_button(Analysis_CH, "Score_Analysis_button_id")
    #起動確認処理実行
    await chack_online.start()


@tasks.loop(seconds=60) #60秒ごとに実行
async def chack_online():
    """毎日定刻に起動チェックを行う"""
    #時刻確認
    now = datetime.datetime.now()
    oncheaktime =now.strftime('%H:%M')

    if oncheaktime == '09:00':
        #管理者DMに起動チェックと対戦Logを送信
        await Creater_DM.send("起動してるよ")
        await Creater_DM.send(file=discord.File(os.environ["SCORE_LOG"]))
        await Creater_DM.send(file=discord.File(os.environ["EXSCORE_LOG"]))


@client.event
async def on_member_join(member):
    """サーバー参加時にロールとユーザー登録を行う"""
    if member.guild.id == Server_ID:
        #入ってきたMemberにBot使用権限ロールを付与
        #role = member.guild.get_role(BotRole_ID)
        #await member.add_roles(role)

        #ユーザーリストに登録
        UserList = pd.read_csv(os.environ["USERLIST"])
        #登録済みなら飛ばす
        if UserList["Discord_ID"].isin([member.id]).any().any():
            pass
        else:
            #登録する
            signup_user = pd.DataFrame([[member.display_name, member.id, 1000, False]], columns=UserList.columns) #新規ユーザーデータを作成
            UserList = pd.concat([UserList, signup_user])
            UserList = UserList.astype({"Discord_ID":"int64", "Rating":"int64"})
            UserList.to_csv(os.environ["USERLIST"], index=False)


#コマンド
@tree.command(name="rand", description="Arkyちゃんにおまかせ!(例:dif=FTR,level=9+,level2=11 ➡ FTR 9+~11)")
async def music_random(ctx, dificullity:str=None, level:str=None, level2:str=None):
    try:
        #ロールが付与されているか
        if await role_check(ctx, BotRole_ID):
            #ランダム選曲チャンネルのみ有効
            if ctx.channel_id == Command_CH:
                music, level_str, dif, image = await Arcaea_command.Random_Select_Level(level, level2, dificullity)

                #応援メッセージを選択
                fanm = ["頑張って!", "ファイトっ!!", "頑張れ!", "応援してるよ!", "全力で行こう!", "力を出して!", "きみなら出来る!", "ふれーふれー!"]
                rand = random.randint(0, len(fanm)-1)
                #ランダムで決まった曲を返信
                return await ctx.response.send_message(f"{ctx.user.mention}さんに課題曲:{music} {dif}:{level_str}だよ! {fanm[rand]}", file=discord.File(image))

            else:
                #利用場所エラー
                return await noaction_message(ctx)
        else:
            #Bot規約エラー
            return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)

    #エラー処理
    except Exception:
        if ctx.channel_id == Creater_DM.id:
            music, level_str, dif, image = await Arcaea_command.Random_Select_Level(level, level2, dificullity)
            return await ctx.response.send_message(f"{music} {dif}:{level_str}", file=discord.File(image))
        else:
            return await ctx.response.send_message("コマンドが間違ってるかも。もう一度試してみて！", ephemeral=True)


@tree.command(name="log", description="対戦記録を表示するよ～")
async def log_view(ctx):
    try:
        if await role_check(ctx, BotRole_ID):
            #対戦チャンネル以外で有効
            if ctx.channel_id != Battle_CH:
                ##Score勝負の結果集計
                file_1vs1_log = os.environ["SCORE_LOG"]
                user = ctx.user #入力したユーザー名を取得
                battledata = await Arcaea_command.User_Status(ctx, user.id, file_1vs1_log)

                #表示用に戦績を整形する
                result = ""
                for _, battle_recode in battledata.iterrows():
                    result += f"**{battle_recode['User']} || W:{battle_recode['Win']}-{battle_recode['Lose']}:L (D:{battle_recode['Drow']})**\n"

                #埋め込みメッセージを作成
                embed = discord.Embed(title="ランダム1v1",description="ランダム1vs1の過去の戦績!!")
                embed.set_author(name=f"{user.display_name}の戦績",icon_url=user.avatar.url)

                #戦績が一件もなかった時は該当なしにする
                if result == "": 
                    embed.add_field(name="通常スコアバトル", value="該当なし", inline=False)
                else:
                    embed.add_field(name="通常スコアバトル", value=result, inline=False)

                #EXScore勝負の結果集計
                file_EX1vs1_log = os.environ["EXSCORE_LOG"]
                battledata = await Arcaea_command.User_Status(ctx, user.id, file_EX1vs1_log)

                #表示用に戦績を整形する
                result = ""
                for _, battle_recode in battledata.iterrows():
                    result += f"**{battle_recode['User']} || W:{battle_recode['Win']}-{battle_recode['Lose']}:L (D:{battle_recode['Drow']})**\n"

                #戦績が一件もなかった時は該当なしにする
                if result == "":
                    embed.add_field(name="EXスコアバトル", value="該当なし", inline=False)
                else:
                    #埋め込みメッセージを作成
                    embed.add_field(name="EXスコアバトル", value=result, inline=False)

                #戦績を送信
                return await ctx.response.send_message(embed=embed)
            else:
                #利用場所エラー
                return await noaction_message(ctx)
        else:
            #Bot規約エラー
            return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)
    
    #エラー処理
    except Exception:
        return await ctx.response.send_message("コマンドが間違ってるかも。もう一度試してみて！", ephemeral=True)


@tree.command(name="tierlist", description="Tierリスト作成のサイトを表示するよ")
async def tierlist_(ctx):
    try:
        if await role_check(ctx, BotRole_ID):
            #ランダム選曲チャンネルのみ有効
            if ctx.channel_id == Command_CH:
                #Arcaea_TierのURLを表示
                await ctx.response.send_message(f"マイTierリストが作れるサイトだよ！遊んでみよ～！\nURL:{Arcaea_Tier_URL}")
            else:
                #利用場所エラー
                return await noaction_message(ctx)
        else:
            #Bot規約エラー
            return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)
    
    #エラー処理
    except Exception:
        return await ctx.response.send_message("予期しないエラーが発生したよ。もう一度試してみて！", ephemeral=True)


@tree.command(name="pt", description="単曲ポテンシャル値の計算をするよ！")
async def potential(ctx, const:float, score:int):
    try:
        if await role_check(ctx, BotRole_ID):
            # コマンドチャンネルのみ有効
            if ctx.channel_id == Command_CH:
                # 
                pt = await Arcaea_command.calc_potential(const, score)
                await ctx.response.send_message(f"譜面定数:{const}\nスコア:{score}\nポテンシャル値:{pt}")
            else:
                # 利用場所エラー
                return await noaction_message(ctx)
        else:
            # Bot規約エラー
            return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)
    
    #エラー処理
    except Exception:
        return await ctx.response.send_message("予期しないエラーが発生したよ。もう一度試してみて！", ephemeral=True)
    

@tree.command(name="omikuji", description="4曲コースおみくじ")
async def omikuji(ctx):
    try:
        if await role_check(ctx, BotRole_ID):
            # コマンドチャンネルのみ有効
            if ctx.channel_id == Command_CH:
                # コースおみくじを引く
                course_name, music_list, music_images = await Arcaea_command.omikuji_course()

                #メッセージ作成
                respon_msg = f"{ctx.user.display_name}さんのコースおみくじの結果は...こちら！"

                if course_name == "No.20  !FUTURE CHALLENGE!":
                    msg = "新旧合戦、いざ決戦！！"
                elif course_name == "No.???  !!!BEYOND CHALLENGE!!!":
                    msg = '**"大吉"**\n己の力を解き放ち、神々を討伐せよ。'
                else:
                    msg = f"{ctx.user.display_name}さんの運勢はどうだったかな？\nぜひ通しで挑戦してみよう！"
                course_msg = f"**{course_name}**\n\n{music_list[0]}{music_list[1]}{music_list[2]}{music_list[3]}\n" + msg
                # 送信
                await ctx.response.send_message(respon_msg)
                await asyncio.sleep(2)
                await ctx.channel.send(course_msg, files=music_images)
            else:
                # 利用場所エラー
                return await noaction_message(ctx)
        else:
            # Bot規約エラー
            return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)
    
    #エラー処理
    except Exception as e:
        return await ctx.response.send_message("予期しないエラーが発生したよ。もう一度試してみて！", ephemeral=True)


@tree.command(name="master_log", description="対戦記録ファイルを出力。(作者のみ)")
async def master_log_view(ctx):
    try:
        #戦績ファイルを出力する(開発者用)
        if ctx.channel_id == Creater_DM.id:
            await ctx.response.send_message(file=discord.File(os.environ["SCORE_LOG"]))
            await ctx.followup.send(file=discord.File(os.environ["EXSCORE_LOG"]))

        else:
            #利用場所エラー
            return await noaction_message(ctx)

    #エラー処理
    except Exception:
        return await ctx.response.send_message("データを正しく出力できませんでした。", ephemeral=True)


@client.event
async def on_message(message):
    try:
        #Botの発言は飛ばす
        if message.author.bot:
            return
        #Arkyちゃんのお部屋でのみ有効
        if message.channel.id != Arky_CH:
            return
        else:
            #ロールチェック
            if await ms_role_check(message, BotRole_ID):
                #GPTにメッセージを送信して結果を表示
                respons = await chatgpt.chatbot_response(message)
                return await message.channel.send(respons)
            else:
                #Bot規約エラー
                return await message.channel.send("Botの使い方を確認してないから使えないよ。確認してきてね！", delete_after=10)

    #エラー処理
    except Exception:
        return await message.channel.send("予期しないエラーが発生したよ。もう一度試してみて！", delete_after=10)


async def show_button(channel_id, message_label):
    """対戦方式選択ボタンを更新する"""
    #表示するチャンネルを取得
    ch = await client.fetch_channel(channel_id)
    
    #前の対戦募集メッセージを削除
    with open(os.environ["VS_DICT"], mode="r") as f:
        file = json.load(f)
        message_id = file["Button_IDs"][message_label]
    #メッセージを取得できない場合は無視
    try:
        message = await ch.fetch_message(message_id)
        await message.delete()
    except discord.NotFound:
        pass
    except discord.errors.HTTPException:
        pass
    
    #選択画面の表示
    if message_label == "BattleSelect_message_id":
        view = ui.VSButton()
        msg = await ch.send("募集したい対戦方法を選んで押してね", view=view)
    elif message_label == "Score_Analysis_button_id":
        view = SA_ui.StartButton()
        msg = await ch.send("スコア分析スレッドを作成するよ", view=view)

    #送信したメッセージのIDを保存
    file["Button_IDs"][message_label] = msg.id
    with open(os.environ["VS_DICT"], mode="w") as f:
        json.dump(file, f, indent=4)

    return


async def noaction_message(ctx):
    """使用できない場所でコマンドを使用したときに送信"""
    await ctx.response.send_message("ここではこのコマンドは使用できません...ごめんね(><)", ephemeral=True)


async def role_check(ctx, role_id):
    """特定のロールが付与されているか"""
    role = ctx.guild.get_role(role_id)
    if role in ctx.user.roles:
        return True
    else:
        return False
    
    
async def ms_role_check(message, role_id):
    """特定のロールが付与されているか(メッセージに対してのみ)"""
    user_role = message.author.roles
    for role in user_role:
        if role.id == role_id:
            return True
        else:
            pass

    return False


#Botを起動
client.run(TOKEN)