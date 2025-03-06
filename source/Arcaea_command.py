import os
import json
import math
import dotenv
import random
import asyncio
import discord
import pandas as pd
from datetime import datetime, timedelta
import ui


async def Random_Select_Level(level1=None, level2=None, dif=None, dif_list:list=None, level_list:list=None):
    """ランダム選曲機能"""
    #ユーザー環境変数を読み込み
    dotenv.load_dotenv()

    #ランダム選曲機能の時
    if level_list == None:
        #レベル指定があるか
        if level1 == None and level2 == None:
            level1, level2 = "0", "12" #全曲指定にする
        elif level1 != None and level2 == None:
            level2 = level1            #単一の難易度のみにする

        #＋難易度が指定された時は.7表記に変更する
        try:
            #引き数を数値型に変換
            level1 = float(level1)
        except ValueError:
            #引き数を数値型に変換
            if level1[-1] == "+":
                level1 = float(level1[:-1]) + 0.7

        try:        
            level2 = float(level2)
        except ValueError:
            if level2[-1] == "+":
                level2 = float(level2[:-1]) + 0.7


        # 楽曲情報をデータフレームに読み込む
        df_music = pd.read_csv(os.environ["MUSIC"])

        # 難易度指定
        if dif != None:
            df_music = df_music[df_music["Difficulty"] == dif]

        # レベル指定
        df_music = df_music[df_music["Level"] >= level1].copy()
        df_range_music = df_music[df_music["Level"] <= level2]


    #対戦の時
    else:
        #楽曲情報をデータフレームに読み込む
        df_music = pd.read_csv(os.environ["MUSIC"])

        # 難易度指定
        df_music = df_music[df_music["Difficulty"].isin(dif_list)]

        # レベル指定
        df_range_music = df_music[df_music["Level"].isin(level_list)]

    #乱数の範囲を取得
    music_num = len(df_range_music)

    #乱数を作成
    rand = random.randint(0,music_num-1)

    #乱数から選ばれた楽曲を抽出
    hit_music = df_range_music.iloc[rand]

    #結果を保存
    title = hit_music["Music_Title"]    # 曲名
    deffecult = hit_music["Difficulty"] # 難易度
    level = hit_music["Level"]          # レベル

    #楽曲レベルを表示用に調整
    if level % 1 != 0.0:
        level_str = str(math.floor(level)) + "+"
    else:
        level_str = str(math.floor(level))

    #画像データを取得
    image = hit_music["Image"]

    return title, level_str, deffecult, image


async def match_host(ctx, user, kind):
    """対戦のホストを立てる"""
    #ロールが付与されてるか確認
    role_id = int(os.environ["BOTROLE_ID"])
    role = ctx.guild.get_role(role_id)
    if role in ctx.user.roles:
        #対戦へ
        pass
    else:
        #Bot規約エラー
        return await ctx.response.send_message("Botの使い方を確認してないから使えないよ。確認してきてね！", ephemeral=True)
    
    #メンバー登録しているか
    #メンバーリストを取得
    UserList = pd.read_csv(os.environ["USERLIST"])
    #登録済みか確認
    if UserList["Discord_ID"].isin([user]).any().any():
        pass
    else:
        return await ctx.response.send_message("メンバー登録が行われていません。OwnerかAdminに問い合わせてしてね", ephemeral=True)
    
    #対戦中、対戦待機中でないか確認
    check = await state_check(user)
    if check:
        return await ctx.response.send_message(f"あなたは対戦中、もしくは対戦ホスト中だよ", ephemeral=True)
        
    with open(os.environ["VS_DICT"], mode="r") as f:
        vs_dict = json.load(f)["VSPattern"]
    #対戦募集ボタンを表示
    role_id = int(os.environ["BOTROLE_ID"])
    view = ui.VSHostButton(user, kind, role_id, timeout=None)
    await ctx.response.send_message("(> <*)", delete_after=0)
    message = await ctx.followup.send(f"{ctx.user.mention}さんが「{vs_dict[kind]}」の募集をしてるよー！", view=view)

    #対戦フラグをDataFrameに登録
    await state_chenge(user, True)

    #10分待って先に進んでいなかったら強制的に終了
    await asyncio.sleep(600)
    if view.stop_flg:
        try:
            #チャンネルを削除
            await message.delete()
            #対戦ステータスを変更
            await state_chenge(user, False)
        except discord.errors.NotFound:
            pass
    else:
        #処理を終わる
        return

async def state_check(user):
    """対戦ステータスを確認する"""
    UserList = pd.read_csv(os.environ["USERLIST"])
    user_state = UserList[UserList["Discord_ID"] == user].copy()
    if user_state["State"].item():
        return True #対戦中
    else:
        return False #未対戦
        

async def state_chenge(user:int, state:bool):
    """対戦ステータスの変更"""
    UserList = pd.read_csv(os.environ["USERLIST"])
    UserList.loc[UserList[UserList["Discord_ID"] == user].index, "State"] = state
    UserList.to_csv(os.environ["USERLIST"], index=False)


async def Arcaea_ScoreBattle(ctx, host_id, guest_id, battle_type):
    """スコアバトルを行う関数"""
    #メンバーリストを取得
    UserList = pd.read_csv(os.environ["USERLIST"])
    #登録済みか確認
    if UserList["Discord_ID"].isin([guest_id]).any().any():
        pass
    else:
        return await ctx.response.send_message("メンバー登録が行われていません。OwnerかAdminに問い合わせてしてね", ephemeral=True)

    #対戦を始める
    #募集メッセージ削除
    await ctx.message.delete()
    #ゲスト側の対戦ステータスを変更
    await state_chenge(guest_id, True)

    #対戦方式によって分岐
    b_type = int(battle_type)

    #ユーザーを取得
    host_user = ctx.client.get_user(host_id)
    guest_user = ctx.client.get_user(guest_id)

    #1vs1対決
    await singles_scorebattlestart(ctx, host_user, guest_user, b_type)
 

async def s_sb_result(ctx, channel, host_user, guest_user, score1, score2, music_ls, b_type):
        #対戦方式によってスコア計算を分岐
        if b_type == 0: #通常スコア対決
            #得点を計算
            winner, loser, player1_score, player2_score = await Score_Battle(score1, score2, host_user, guest_user)
        elif b_type == 1: #EXスコア対決
            #得点を計算
            winner, loser, player1_score, player2_score, Drow_Flg = await EX_Score_Battle(score1, score2, host_user, guest_user)

        #名前を変数に
        host_name = host_user.display_name
        guest_name = guest_user.display_name

        #勝敗をスレッドに表示
        if b_type == 0:
            #通常スコアバトル
            vs_format = "ScoreBattle"
            if player1_score == player2_score:
                await channel.send(f"結果は両者 {player1_score:,} で引き分け!! 白熱した戦いだったね!")
                Drow_Flg = True
                #表示用のリザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(score1[0]):,}\n{guest_name}：{int(score2[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(score1[1]):,}\n{guest_name}：{int(score2[1]):,}\n"\
                         f"・Total\n{host_name}：{player1_score:,}\n{guest_name}：{player2_score:,}\n\n"\
                         f"Drow：{winner.display_name} {loser.display_name}!!"

            else:
                await channel.send(f"{host_name}: {player1_score:,}\n{guest_name}: {player2_score:,}\n\n勝者は{winner.mention}さん!!おめでとう!!🎉🎉")
                Drow_Flg = False
                #表示用のリザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(score1[0]):,}\n{guest_name}：{int(score2[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(score1[1]):,}\n{guest_name}：{int(score2[1]):,}\n"\
                         f"・Total\n{host_name}：{player1_score:,}\n{guest_name}：{player2_score:,}\n\n"\
                         f"Winner：{winner.display_name}!!"
                
        elif b_type == 1: #EXスコア対決
            #EXスコアバトル
            vs_format = "EXScoreBattle"
            if sum(player1_score) == sum(player2_score):
                await channel.send(f"結果は両者 {sum(player1_score):,} で引き分け!! 白熱した戦いだったね!")
                Drow_Flg = True
                #表示用のリザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(player1_score[0]):,}\n{guest_name}：{int(player2_score[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(player1_score[1]):,}\n{guest_name}：{int(player2_score[1]):,}\n"\
                         f"・Total\n{host_name}：{sum(player1_score):,}\n{guest_name}：{sum(player2_score):,}\n\n"\
                         f"{winner.display_name}さんvs{loser.display_name}さんは引き分けでした!!!"

            else:
                await channel.send(f"{host_name}: {sum(player1_score):,}\n{guest_name}: {sum(player2_score):,}\n\n勝者は{winner.mention}さん!!おめでとう!!🎉🎉")
                Drow_Flg = False
                #表示用のリザルトを作成
                result = f"[{vs_format}]\n"\
                         f"・1曲目 {music_ls[0]}\n{host_name}：{int(player1_score[0]):,}\n{guest_name}：{int(player2_score[0]):,}\n"\
                         f"・2曲目 {music_ls[1]}\n{host_name}：{int(player1_score[1]):,}\n{guest_name}：{int(player2_score[1]):,}\n"\
                         f"・Total\n{host_name}：{sum(player1_score):,}\n{guest_name}：{sum(player2_score):,}\n\n"\
                         f"勝者は{winner.display_name}さんでした!!!"


        #csvファイルに保存
        if b_type == 0: #通常スコア
            log_path = os.environ["SCORE_LOG"]
        else:           #EXスコア
            log_path = os.environ["EXSCORE_LOG"]
        df_log = pd.read_csv(log_path)
        now_data = [[winner.id, loser.id, Drow_Flg]]
        df_now = pd.DataFrame(now_data, columns=["Winner", "Loser", "Drow_Flg"])
        df_log = pd.concat([df_log, df_now])
        df_log.to_csv(log_path, index=False)

        #対戦結果をチャンネルに表示
        result_ch = await ctx.client.fetch_channel(int(os.environ["B_RESULT_CH"]))
        await result_ch.send(result)

        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)

        #30秒後スレッドを閉じる
        await asyncio.sleep(1) #間を空ける
        await channel.send(f"このチャンネルは1分後に自動で削除されるよ\nおつかれさま～～!またね!!")
        await asyncio.sleep(60) #スレッド削除まで待機
        await channel.delete() #スレッドを削除


#1vs1で戦う時のフォーマット
async def singles_scorebattlestart(ctx, host_user, guest_user, EX_flg):
    #勝負形式を取得
    if EX_flg == 1:
        vs_format = "EXScoreBattle"
    else:
        vs_format = "ScoreBattle"

    #対戦スレッドを作成
    channel_category= await ctx.client.fetch_channel(int(os.environ["THREAD_CH"]))
    channel = await channel_category.create_text_channel(name="{} vs {}：{}".format(host_user.display_name, guest_user.display_name, vs_format))

    #スレッド内でのエラーをキャッチ
    try:
        #リンクプレイコードのチェック
        def checkLinkID(m):
            try:
                ms = m.content
                if len(ms) == 6:
                    str(ms[0:4])
                    int(ms[4:6])
                    return True
            except Exception:
                return False

        #メッセージとボタンを作成
        an = f"Channel：{channel.mention} \n {host_user.display_name} vs {guest_user.display_name}"
        ms = f"Channel：{host_user.mention} vs {guest_user.mention} \n (途中終了する時はお互いに「終了」を押してね)"
        b_stop = ui.VSStopbutton(host_user.id, guest_user.id, timeout=None)

        #メッセージを送信して難易度選択を待機
        await ctx.response.send_message(an, delete_after=30)
        await channel.send(ms, view=b_stop)
        await channel.send(f"{host_user.mention}:Link Playのルームを作成して、ルームコードを入力してね")

        #メッセージを受け取ったスレッドに対してのみ返す
        while True:
            msg = await ctx.client.wait_for('message', check=checkLinkID, timeout=600)
            #同一スレッドかつホストの入力であるか確認
            if channel.id == msg.channel.id and host_user.id == msg.author.id:
                break
            else:
                pass

        await asyncio.sleep(0.5) #インターバル

        #課題曲難易度選択のボタンを表示
        view = ui.VSMusicDifChoice(host_user.id, guest_user.id, EX_flg, timeout=600)
        await channel.send("難易度を選択してね!お互いがOKを押したら次に進むよ",view=view)
        await asyncio.sleep(600) #待機
        #10分待って先に進んでいなかったら強制的に終了
        if view.stop_flg:
            try:
                #チャンネルを削除
                await channel.delete()
                #対戦ステータスを変更
                await state_chenge(host_user.id, False)
                await state_chenge(guest_user.id, False)
            except discord.errors.NotFound:
                pass
        else:
            #処理を終わる
            return

    #スレッド内でトラブルが起こったらスレッドを閉じる
    except Exception:
        await asyncio.sleep(1) #間を空ける
        await channel.send("タイムアウトより対戦が終了されたよ。チャンネルを削除するね")
        await asyncio.sleep(3) #スレッド削除まで待機
        await channel.delete()
        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)


async def s_sb_selectlevel(ctx, host_user_id, guest_user_id, dif_ls, EX_flg):
    """レベル選択ボタンを表示"""
    view = ui.VSMusicLevelChoice(host_user_id, guest_user_id, dif_ls, EX_flg, timeout=600)
    await ctx.followup.send("レベルを選択してね!お互いがOKを押したら次に進むよ",view=view)
    await asyncio.sleep(600)
    #10分待って先に進んでいなかったら強制的に終了
    if view.stop_flg:
        try:
            #チャンネルを削除
            await ctx.channel.delete()
            #対戦ステータスを変更
            await state_chenge(host_user_id, False)
            await state_chenge(guest_user_id, False)
        except discord.errors.NotFound:
            pass
    else:
        #処理を終わる
        return


async def s_sb_musicselect(ctx, host_user_id, guest_user_id, dif_ls, level_ls, EX_flg, Score_Count=None):
    """楽曲表示と決定処理"""
    music, level_str, dif, image = await Random_Select_Level(dif_list=dif_ls, level_list=level_ls)
    #対戦開始前のメッセージを作成
    musicmsg = f"対戦曲:[{music}] {dif}:{level_str}!!"
    music = f"{music} {dif} {level_str}"
    #選択のボタンを表示
    view = ui.VSMusicButton(host_user_id, guest_user_id, dif_ls, level_ls, music, EX_flg, Score_Count, timeout=600)
    #課題曲を表示
    await ctx.channel.send(musicmsg, file=discord.File(image), view=view)
    await ctx.channel.send("お互いが選択したらゲームスタート!!")
    await asyncio.sleep(600)
    #10分待って先に進んでいなかったら強制的に終了
    if view.stop_flg:
        try:
            #チャンネルを削除
            await ctx.channel.delete()
            #対戦ステータスを変更
            await state_chenge(host_user_id, False)
            await state_chenge(guest_user_id, False)
        except discord.errors.NotFound:
            pass
    else:
        #処理を終わる
        return


async def s_sb_battle(ctx, host_user_id, guest_user_id, dif_ls, level_ls, music, EX_flg, Score_Count=None):
    """スコア受け取りから終了まで"""
    try:
        #初回の場合はインスタンス作成
        if Score_Count != None:
            pass
        else:
            Score_Count = ScoreManage()

        #チャンネル属性を取得
        channel = ctx.channel
        #ユーザー属性を取得
        host_user =  ctx.client.get_user(host_user_id)
        guest_user =  ctx.client.get_user(guest_user_id)

        #スコア受け取り監視関数を定義
        def check(m):
            """通常スコア用チェック関数"""
            try:
                ms = m.content.split(' ')
                if len(ms) == 1:
                    for i in ms:
                        int(i)
                    return True
            except Exception:
                return False

        def checkEX(m):
            """EXスコア用チェック関数"""
            try:
                ms = m.content.split(' ')
                if len(ms) == 4:
                    for i in ms:
                        int(i)
                    return True
            except Exception:
                return False

        #一人目
        if EX_flg == False: #通常スコア
        #メッセージ送信
            await channel.send(f"{host_user.mention}さんのスコアを入力してね")
            while True:
                BattleRisult1 = await ctx.client.wait_for('message', check=check, timeout=600)
                #メッセージを受け取ったスレッドであるか、メンションされたユーザーからであるかを確認
                if channel.id == BattleRisult1.channel.id and host_user.id == BattleRisult1.author.id:
                    #スコア確認ボタンを押す
                    view = ui.VSScoreCheck(host_user_id)
                    await channel.send(f"入力スコア「{int(BattleRisult1.content):,}」でOKかな？", view=view)
                    stasrt_time = datetime.now() 
                    timeout = stasrt_time + timedelta(minutes=10)
                    while True:
                        #時刻を取得
                        nowtime = datetime.now()
                        #次に進む
                        if view.start_flg or view.reinput_flg:
                            break
                        #終了する
                        elif nowtime >= timeout:
                            try:
                                #チャンネルを削除
                                await ctx.channel.delete()
                                #対戦ステータスを変更
                                await state_chenge(host_user_id, False)
                                await state_chenge(guest_user_id, False)
                                return #終わる
                            except discord.errors.NotFound:
                                return #終わる
                        else:
                            await asyncio.sleep(1)
                    
                    #スコアの入力しなおしへ        
                    if view.reinput_flg:
                        pass
                    #次に進む
                    else:
                        break
                else:
                    pass

        else:               #EXスコア
            #メッセージ送信
            await channel.send(f"{host_user.mention}さんのEXスコアを入力してね\n 例:1430 1392 13 7 (pure数,内部pure数,far数,lost数)")
            while True:
                BattleRisult1 = await ctx.client.wait_for('message', check=checkEX, timeout=600)
                #メッセージを受け取ったスレッドであるか、メンションされたユーザーからであるかを確認
                if channel.id == BattleRisult1.channel.id and host_user.id == BattleRisult1.author.id:
                    break
                else:
                    pass

        #二人目
        if EX_flg == False: #通常スコア
            #メッセージ送信
            await channel.send(f"{guest_user.mention}さんのスコアを入力してね")
            while True:
                BattleRisult2 = await ctx.client.wait_for('message', check=check, timeout=600)
                #メッセージを受け取ったスレッドであるか、メンションされたユーザーからであるかを確認
                if channel.id == BattleRisult2.channel.id and guest_user.id == BattleRisult2.author.id:
                    view = ui.VSScoreCheck(guest_user_id)
                    await channel.send(f"入力スコア「{int(BattleRisult2.content):,}」でOKかな？", view=view)
                    stasrt_time = datetime.now() 
                    timeout = stasrt_time + timedelta(minutes=10)
                    while True:
                        #時刻を取得
                        nowtime = datetime.now()
                        #次に進む
                        if view.start_flg or view.reinput_flg:
                            break
                        #終了する
                        elif nowtime >= timeout:
                            try:
                                #チャンネルを削除
                                await ctx.channel.delete()
                                #対戦ステータスを変更
                                await state_chenge(host_user_id, False)
                                await state_chenge(guest_user_id, False)
                                return #終わる
                            except discord.errors.NotFound:
                                return #終わる
                        else:
                            await asyncio.sleep(1)
                    
                    #スコアの入力しなおしへ        
                    if view.reinput_flg:
                        pass
                    #次に進む
                    else:
                        break
                else:
                    pass

        else:               #EXスコア
            #メッセージ送信
            await channel.send(f"{guest_user.mention}さんのスコアを入力してね\n 例:1430 1392 13 7 (pure数,内部pure数,far数,lost数)")
            while True:
                BattleRisult2 = await ctx.client.wait_for('message', check=checkEX, timeout=600)
                #メッセージを受け取ったスレッドであるか、メンションされたユーザーからであるかを確認
                if channel.id == BattleRisult2.channel.id and guest_user.id == BattleRisult2.author.id:
                    break
                else:
                    pass 
                            
        await asyncio.sleep(1) #インターバル

        #スコアをlistに保存
        Score_Count.score1.append(BattleRisult1.content)
        Score_Count.score2.append(BattleRisult2.content)

        #対戦曲数を数える
        Score_Count.count += 1

        #選択曲をレコード用に取得
        Score_Count.music_ls.append(music)

        #最終曲になったらループを抜ける
        if Score_Count.count == 2:
            await channel.send(f"対戦終了～～！！ 対戦結果は～～？")
            await asyncio.sleep(3)

            #スコア計算、結果表示関数
            await s_sb_result(ctx, channel, host_user, guest_user, Score_Count.score1, Score_Count.score2, Score_Count.music_ls, EX_flg)
        else:
            await channel.send(f"{Score_Count.count}曲目おつかれさま！！ {Score_Count.count+1}曲目はなにがでるかな～")
            await asyncio.sleep(3)
            #楽曲選択に移行
            await s_sb_musicselect(ctx, host_user_id, guest_user_id, dif_ls, level_ls, EX_flg, Score_Count)

    #スレッド内でトラブルが起こったらスレッドを閉じる
    except Exception as e:
        print(e)
        await asyncio.sleep(1) #間を空ける
        await channel.send("タイムアウトより対戦が終了されたよ。チャンネルを削除するね")
        await asyncio.sleep(3) #スレッド削除まで待機
        await channel.delete()
        #対戦ステータスを変更
        await state_chenge(host_user.id, False)
        await state_chenge(guest_user.id, False)

class ScoreManage():
    """対戦のスコアを一時保存するためのクラス"""
    def __init__(self):
        self.score1 = []
        self.score2 = []
        self.music_ls = []
        self.count = 0
        
        
async def calc_potential(const, score):
    """ポテンシャル値を計算"""
    # 計算に使用する定数
    pm = 10000000
    ex = 9800000
    aa = 9500000
    
    # スコア別ポテンシャル計算
    if score >= pm: # PM以上
        potential = const + 2.0
             
    elif score >= ex: # EX以上
        potential = const + 1.0 + (score - ex)/200000
        
    else: # EX以下
        potential = const + (score - aa)/300000
        # ポテンシャルの下限は0
        if potential < 0:
           potential = 0
        
    return round(potential, 3)


#ダブルススコアバトルを行う関数
#async def Doubles_RandomScoreBattle(client, message):
#    #渡されたコマンドを分割
#    comannd = message.content.split(' ')
#    users = [comannd[2], comannd[3], comannd[4], comannd[5]]
#    users_id = [int(user[2:-1]) for user in users]
#
#    if len(comannd) == 6 and len(users) == len(set(users)):
#        username_1 = client.get_user(users_id[0]).display_name
#        username_2 = client.get_user(users_id[2]).display_name
#        #対戦スレッドを作成
#        thread = await message.channel.create_thread(name="{}チーム vs {}チーム：ScoreBattle".format(username_1, username_2),type=discord.ChannelType.public_thread)
#
#        #スレッド内でのエラーをキャッチ
#        try:
#            #難易度選択時のメッセージチェック関数
#            def checkLv(m):
#                try:
#                    ms = m.content.split() #受け取ったメッセージをlistに
#                    for n in ms:
#                        if n[-1] == "+":
#                            float(n[:-1]) #数値であるか検証
#                        elif n == "all":
#                            pass
#                        else:
#                            float(n) #数値であるか判定
#                    return True
#                except Exception:
#                    return False
#
#            an = f"スレッド：{thread.mention} \n {username_1}チームと{username_2}チームのスコア対戦を開始します"
#            ms = f"{users[0]}, {users[1]}チームと{users[2]}, {users[3]}チーム \n 120秒以内に難易度を選択して下さい(全曲の場合は「all」と入力してください)"
#
#            #メッセージを送信して難易度選択を待機
#            await message.channel.send(an)
#            await thread.send(ms)            
#
#            #メッセージを受け取ったスレッドに対してのみ返す
#            while True:
#                msg = await client.wait_for('message', check=checkLv, timeout=120)
#
#                if thread.id == msg.channel.id:
#                    break
#                else:
#                    pass
#
#            #渡されたコマンドを分割
#            select_difficult = msg.content.split(' ')
#
#            team1, team2, music_ls = [], [], []
#
#            N_music = 2 #対戦曲数を指定(基本的に2)
#            count = 0 #何曲目かをカウントする
#
#            while True:
#                #難易度を指定していない時
#                if select_difficult[0] == "ALL" or select_difficult[0] == "all":
#                    music, level_str, dif = Random_Select_Level()
#
#                #難易度の上下限を指定している時
#                elif len(select_difficult) == 2:
#                    level_low = select_difficult[0]
#                    level_high = select_difficult[1]
#                    music, level_str, dif = Random_Select_Level(level_low, level_high)
#
#                #難易度を指定している時
#                elif len(select_difficult) == 1:
#                    level = select_difficult[0]
#                    music, level_str, dif = Random_Select_Level(level)
#
#                #対戦開始前のメッセージを作成
#                startmsg = f"対戦曲は[{music}] {dif}:{level_str}です!!\n\n10分以内に楽曲を終了してスコアを入力してね。\n例:9950231\n(対戦を途中終了する時は、チームの１人目が「終了」と入力してください)"
#                await asyncio.sleep(1)
#                await thread.send(startmsg)
#                await asyncio.sleep(0.5)
#
#                #スコア報告チェック関数
#                def check(m):
#                    try:
#                        ms = m.content.split(' ')
#                        if len(ms) == 1:
#                            for i in ms:
#                                int(i)
#                            return True
#                    except Exception:
#                        if m.content == "終了" or m.content == "引き直し": #終了か引き直しと入力した場合のみok
#                            return True
#                        return False
#
#                #team1のスコアを集計
#                await thread.send(f"{users[0]}チーム１人目のスコアを入力してね。\n楽曲を再選択する場合は「引き直し」と入力してください")
#                #メッセージを受け取ったスレッドに対してのみ返す
#                while True:
#                    BattleRisult1 = await client.wait_for('message', check=check, timeout=600)
#                    if thread.id == BattleRisult1.channel.id:
#                        break
#                    else:
#                        pass
#                        
#                await asyncio.sleep(1)
#                #引き直しが選択されたら選曲まで戻る
#                if BattleRisult1.content == "引き直し":
#                    continue
#
#                await thread.send(f"{users[0]}チーム２人目のスコアを入力してね。(5分以内)")
#                #メッセージを受け取ったスレッドに対してのみ返す
#                while True:
#                    BattleRisult2 = await client.wait_for('message', check=check, timeout=300)
#                    if thread.id == BattleRisult2.channel.id:
#                        break
#                    else:
#                        pass
#                        
#                await asyncio.sleep(1)
#
#                #team1のスコアをリストに追加
#                team1.append(BattleRisult1.content)
#                team1.append(BattleRisult2.content)
#
#                #team2のスコアを集計
#                await thread.send(f"{users[2]}チーム１人目のスコアを入力してね。(5分以内)")
#                #メッセージを受け取ったスレッドに対してのみ返す
#                while True:
#                    BattleRisult3 = await client.wait_for('message', check=check, timeout=600)
#                    if thread.id == BattleRisult3.channel.id:
#                        break
#                    else:
#                        pass
#                        
#                await asyncio.sleep(1)
#
#                await thread.send(f"{users[2]}チーム２人目のスコアを入力してね。(5分以内)")
#                #メッセージを受け取ったスレッドに対してのみ返す
#                while True:
#                    BattleRisult4 = await client.wait_for('message', check=check, timeout=600)
#                    if thread.id == BattleRisult4.channel.id:
#                        break
#                    else:
#                        pass
#                        
#                await asyncio.sleep(1)
#
#                #team2のスコアをリストに追加
#                team2.append(BattleRisult3.content)
#                team2.append(BattleRisult4.content)
#
#                #どちらかが終了と入力したら終わる
#                if BattleRisult1.content == "終了" or BattleRisult3.content == "終了":
#                    await thread.send(f"対戦が途中で終了されました。お疲れ様でした。")
#                    await asyncio.sleep(3)
#                    await thread.delete()
#                    return 
#
#                #対戦曲数を数える
#                count += 1
#
#                #選択曲をレコード用に取得
#                music_ls.append(f"{music} {dif} {level_str}")
#
#                #最終曲になったらループを抜ける
#                if count == N_music:
#                    await thread.send(f"対戦が終了ました。結果を集計します。")
#                    await asyncio.sleep(3)
#                    break
#
#                await thread.send(f"{count}曲目お疲れ様でした！！ {count+1}曲目の選曲を行います。")
#                await asyncio.sleep(3)
#
#            return thread, team1, team2, users, music_ls
#
#        #スレッド内でトラブルが起こったらスレッドを閉じる
#        except Exception:
#            await asyncio.sleep(1) #間を空ける
#            await thread.send("タイムアウト、もしくはコマンド不備により対戦が終了されました。スレッドを削除します。")
#            await asyncio.sleep(3) #スレッド削除まで待機
#            await thread.delete()
#
#    else:
#        #例外処理に持っていく
#        raise Exception("")


#スコア対決の計算
async def Score_Battle(user1, user2, name1, name2):

    #対戦者名とスコアを取得
    user1_score = 0
    user2_score = 0
    for score1, score2 in zip(user1, user2):

        user1_score += int(score1)
        user2_score += int(score2)

    if user1_score > user2_score:    #user1の勝利
        return name1, name2, user1_score, user2_score
    elif user1_score == user2_score: #引き分け
        return name1, name2, user1_score, user2_score
    else:                            #user2の勝利
        return name2, name1, user1_score, user2_score


#EXスコア対決の計算
async def EX_Score_Battle(user1, user2, name1, name2):

    #対戦者名とスコアを取得
    user1_score = 0
    user2_score = 0
    total_P_pure1 = 0
    total_P_pure2 = 0
    user1_score_ls = []
    user2_score_ls = []

    for score1, score2 in zip(user1, user2):
        #EXスコアを計算(無印Pure:3点,Pure:2点,Far:1点,Lost:0点)
        #1Pプレイヤーのスコアを計算
        pure1, P_pure1, far1, lost1 = score1.split(' ')
        F_pure1 = int(pure1) - int(P_pure1)
        user1_score += int(P_pure1)*3 + int(F_pure1)*2 + int(far1)*1
        total_P_pure1 += int(P_pure1)
        user1_score_ls.append(int(P_pure1)*3 + int(F_pure1)*2 + int(far1)*1)

        #2Pプレイヤーのスコアを計算
        pure2, P_pure2, far2, lost2 = score2.split(' ')
        F_pure2 = int(pure2) - int(P_pure2)
        user2_score += int(P_pure2)*3 + int(F_pure2)*2 + int(far2)*1
        total_P_pure2 += int(P_pure1)
        user2_score_ls.append(int(P_pure2)*3 + int(F_pure2)*2 + int(far2)*1)

    if user1_score > user2_score:   #user1の勝利
        Drow_Flg = False
        return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg
    elif user1_score < user2_score: #user2の勝利
        Drow_Flg = False
        return name2, name1, user1_score_ls, user2_score_ls, Drow_Flg
    else:                           #EXスコアが引き分けのときは内部精度勝負
        if total_P_pure1 > total_P_pure2:   #user1の勝利
            Drow_Flg = False
            return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg
        elif total_P_pure1 < total_P_pure2: #user2の勝利
            Drow_Flg = False
            return name2, name1, user1_score_ls, user2_score_ls, Drow_Flg
        else:                               #それでも結果がつかなかった場合引き分け
            Drow_Flg = True
            return name1, name2, user1_score_ls, user2_score_ls, Drow_Flg


#戦績を確認
async def User_Status(ctx, user, file_path):
    #データを読み込んで加工しやすいように前処理
    BattleLog = pd.read_csv(file_path)
    BattleLog["Winner"] = BattleLog["Winner"].astype("Int64")
    BattleLog["Loser"] = BattleLog["Loser"].astype("Int64")
    wins = BattleLog[BattleLog["Winner"] == user]
    loses = BattleLog[BattleLog["Loser"] == user]
    userdata = pd.concat([wins, loses])

    #引き分け行に前処理を行う
    idx = 0
    for recode in userdata.itertuples():
        if recode.Drow_Flg == True:
            if recode.Winner == user:
                pass
            else:
                userdata.loc[idx, "Loser"] == userdata.loc[idx, "Winner"]
                userdata.loc[idx, "Winner"] == user

    #重複行を纏める
    margedata = userdata.drop_duplicates()
    #結果を保存するデータフレームを作成
    result = pd.DataFrame(columns=["User"])

    #対戦した相手をUserとしてデータフレームに登録していく
    for idx, recode in margedata.iterrows():
        if recode["Winner"] == user: #勝ってたとき
            if (result["User"] == recode["Loser"]).any():
                pass
            else:
                new_user = pd.DataFrame({"User":[recode["Loser"]]})
                result = pd.concat([result, new_user])
        elif recode.Loser == user: #負けてたとき
            if (result["User"] == recode["Winner"]).any():
                pass
            else:
                new_user = pd.DataFrame({"User":[recode["Winner"]]})
                result = pd.concat([result, new_user])

    #勝敗結果を記録するために列を追加、インデックスを追加
    result = result.assign(Win=0, Lose=0, Drow=0)
    result.index = range(len(result))

    #与えられたデータを上から流していく
    for _, recode in userdata.iterrows():
        if recode["Winner"] == user and recode["Drow_Flg"] == False: #入力者が勝者の場合
            idx = result.index[result["User"] == recode["Loser"]]
            result.loc[idx, "Win"] += 1 
        elif recode["Loser"] == user and recode["Drow_Flg"] == False: #入力者が敗者の場合
            idx = result.index[result["User"] == recode["Winner"]]
            result.loc[idx,"Lose"] += 1
        elif recode["Drow_Flg"] == True:
            if recode["Winner"] == user:
                idx = result.index[result["User"] == recode["Loser"]]
                result.loc[idx,"Drow"] += 1
            elif recode["Loser"] == user:
                idx = result.index[result["User"] == recode["Winner"]]
                result.loc[idx,"Drow"] += 1

    #名前を表示名に変更する
    for idx, recode in result.iterrows():
        result.loc[idx, "User"] = (await ctx.client.fetch_user(recode["User"])).display_name

    #集計が終了したデータを勝利→引き分け→敗北にソートして返す
    return result.sort_values(by=["Win", "Drow", "Lose"])


async def omikuji_course():
    """作成したコースをランダムで選ぶ"""
    course_list = [
        ["No.1  Study Set", [284, 84, 218, 30]], # prism/bookmaker/paper witch/Chronostasis
        ["No.2  Double Name Set", [240, 68, 47, 347]], # quon/quon/genesis/genesis
        ["No.3  Hop Step Jump ↓ Set", [200, 270, 193, 326]], # dazzle hop /final step / Jump / freef4ll
        ["No.4  Rainbow Set", [446, 54, 195, 374]], # エピクロス/red and blue/purple/RGB
        ["No.5  Season Set", [43, 258, 271, 106]], # ハルトピア/彩る夏の恋花火/秋の陽炎/empire of winter
        ["No.6  World Set", [24, 441, 474, 377]], # brand new/floating/inverted/rise of the
        ["No.7  Weather Set", [259, 490, 234, 506]], # first snow/third sun/small cloud sugar candy/lament rain
        ["No.8  Numbers Set", [86, 145, 204, 135]], # 9番目/no.1/7th/valhalla0
        ['No.9  "The" Set', [407, 87, 228, 358]], # formula/message/ultimacy/milky way
        ["No.10  Alter Set", [297, 235, 167, 466]], # altair/alterale/altale/ALTER EGO
        ["No.11  Astra Set", [104, 495, 331, 508]], # tale/.exe/walkthrough/quanti
        ["No.12  Return Set", [153, 434, 93, 211]], # amygdata/MORNINGROOM/dropdead/AttraqtiA
        ["No.13  Love Set", [213, 354, 133, 427]], # enchanted love/galactic love/迷える/狂恋
        ["No.14  Happy new year!! Set", [404, 53, 348, 206]], # on and on/ドリーミン/trrricksters/アメマイ
        ["No.15  One character Set", [98, 317, 214, 371]], # 光/心/竹/Ⅱ
        ["No.16  Overflow Set", [227, 248, 101, 394]], # ターボ/ESM/アクセラレーター/テラボルト
        ["No.17  ∞ Set", [22, 316, 340, 310]], # heaven/eternity/[x]/Strife
        ["No.18  Light vs Conflict Set", [220, 342, 58, 479]], # far away light/PRIMITIVE LIGHTS/conflict/Rain of Conflict in a Radiant Abyss
        ["No.19  Subtitle Set", [57, 111, 236, 210]], # 妖艶/光速/業/ウロボ
        ["No.20  !FUTURE CHALLENGE!", [60, 91, 379, 390]], # Grievous Lady/Fracture Ray/Abstruse Dilemma/Arghena
        ["No.???  !!!BEYOND CHALLENGE!!!", [268, 313, 513, 314]] # PRAGMATISM -RESURRECTION-/Arcana Eden/Designant./Testify
        ]
    
    # 楽曲情報をデータフレームに読み込む
    df_music = pd.read_csv(os.environ["MUSIC"])

    # ランダムで選ぶ
    pick_course = course_list[random.randint(0,len(course_list)-1)]
    course_name = pick_course[0]
    course_musicnumbers = pick_course[1]

    music_list = []
    music_images = []
    count = 1
    # ソート番号から楽曲を取得
    for number in course_musicnumbers:
        music = df_music[df_music["SortNo"] == number] # 取得
        #楽曲レベルを表示用に調整
        if float(music["Level"].values[0]) % 1 != 0.0:
            level_str = str(math.floor(music["Level"].values[0])) + "+"
        else:
            level_str = str(math.floor(music["Level"].values[0]))
        music_list.append(f"{count}曲目 「{str(music['Music_Title'].values[0])}」{str(music['Difficulty'].values[0])}:{level_str}\n") # 追加
        music_images.append(discord.File(str(music["Image"].values[0])))

        count += 1

    return course_name, music_list, music_images