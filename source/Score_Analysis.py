import os
import dotenv
import asyncio
import discord
import subprocess
import pandas as pd
import Score_Analysis_ui as SA_ui

# ユーザー環境変数を読み込み
dotenv.load_dotenv()

# 定数設定
PM = 10000000
EXPLUS = 9900000
EX = 9800000
AA = 9500000

#-----ui側-----------------------------------------------------------------------
async def score_analysis(ctx):
    """個人のスコア分析スレッドを作成する"""
    try:
        #プライベートスレッドを作成
        thread_ch = await ctx.client.fetch_channel(int(os.environ["ANALYSIS_CH"]))
        thread = await thread_ch.create_thread(name=f"{ctx.user.display_name} Thread", type=None)
        await ctx.response.send_message("スレッドを作成したよ。移動してね！", delete_after=20)
        await thread.send(ctx.user.mention) #スレッドでメンションをかける
                    
        #初回登録を行っているか
        df_p_user = pd.read_csv(os.environ["P_USERLIST"])
        if df_p_user["Discord_ID"].isin([ctx.user.id]).any().any():
            #スタートメニューへ移行
            await start_menu(ctx, thread)
        else:
            #初回登録を行わせる
            await signup(ctx, thread)

    #スレッド内でトラブルが起こったらスレッドを閉じる
    except Exception as e:
        await asyncio.sleep(1) #間を空ける
        await thread.send("問題が発生したよ、チャンネルを削除するね")
        await asyncio.sleep(3) #スレッド削除まで待機
        await thread.delete()


async def signup(ctx, thread):
    """初回登録を行う"""
    try:
        await thread.send("識別ユーザー名を決めてね(半角英数のみ)")
        await asyncio.sleep(1)
        name = await ctx.client.wait_for('message', timeout=600)
        view = SA_ui.CheckButton(ctx, thread, name.content)
        await thread.send(f"ユーザー名「{name.content}」でOKかな？", view=view)
    except Exception:
        await thread.delete()
        
async def namecheck(ctx, thread, name):
    """識別名チェックと登録"""
    df_p_user = pd.read_csv(os.environ["P_USERLIST"])
    if df_p_user["UserName"].isin([name]).any().any():
        #名前を再入力させる
        await thread.send("登録した名前は既に使われているよ、他の名前を入力してね")
        await signup(ctx, thread)
    else:
        #ユーザー登録を行う
        signup_user = pd.DataFrame([[ctx.user.id, name, "default"]], columns=df_p_user.columns) #新規ユーザーデータを作成
        df_p_user = pd.concat([df_p_user, signup_user])
        df_p_user = df_p_user.astype({"Discord_ID":"int64"})
        df_p_user.to_csv(os.environ["P_USERLIST"], index=False)
        await thread.send("登録完了！よろしくね") #登録成功を伝える
        #スタートメニューに移動
        await start_menu(ctx, thread)
        
        
async def start_menu(ctx, thread):
    """スレッド内初期状態を作成する"""
    #メッセージを作成して送信
    msg = f"やっほー！{ctx.user.display_name}さん！ 今日はなににする？"
    view = SA_ui.MenuButten()
    await thread.send(msg,view=view)

    #10分無操作でスレッド削除
    for i in range(1,11):
        if view.delete_flg == True and i == 10:
            #10分間無操作の時
            await thread.send("10分間操作されなかったからスレッドを削除するよ、またね！")
            await asyncio.sleep(1)
            await thread.delete()
        elif view.delete_flg == False:
            #操作されてた場合は処理を終了
            break
        else:
            #一分待って再度確認
            await asyncio.sleep(60)

async def file_register(ctx, user):
    """スコア登録を行う"""
    try:
        def check(m):
            """ファイル形式チェック関数"""
            # メッセージに添付されたファイルがあるか確認
            if m.attachments:
                for attachment in m.attachments:
                    #ファイルがExcelファイルであることを確認
                    if attachment.filename.endswith('.xlsx'):
                        return True
                    else:
                        return False
            else:
                return False

        #ファイルを受け取る(待機時間10分)
        await ctx.followup.send("ファイルを送信してね！")
        msg = await ctx.client.wait_for('message', check=check, timeout=600)
    
        #PListを取得
        df_p_user = pd.read_csv(os.environ["P_USERLIST"])
        #登録名を取得
        name = df_p_user.loc[df_p_user[df_p_user["Discord_ID"] == user.id].index, "UserName"].iloc[0]
        
        #ファイルを保存
        for attachment in msg.attachments:
            # ファイルがExcelファイルであることを確認
            if attachment.filename.endswith('.xlsx'):
                # ファイルを保存
                file_path = f"./data/score/{name}.xlsx"
                await attachment.save(file_path)
                #ファイルの権限を設定
                try:
                    subprocess.run(["sudo", "chmod", "777", file_path], check=True)
                except Exception as e:
                    await ctx.followup.send(f"erorr:{e}が発生しました")
        
        #パスをListに追加
        df_p_user.loc[df_p_user[df_p_user["Discord_ID"] == user.id].index, "Score_Path"] = file_path
        df_p_user.to_csv(os.environ["P_USERLIST"], index=False)

        #登録完了を知らせる
        await ctx.followup.send("登録が完了したよ！\n")

        #メニューを再度表示
        await asyncio.sleep(2)
        await start_menu(ctx, ctx.channel)

    except Exception as e:
        await ctx.followup.send("一定時間ファイルが送信されなかったからメニューにもどるよ")
        #メニューを再度表示
        await asyncio.sleep(2)
        await start_menu(ctx, ctx.channel)
        

#-----内部処理側------------------------------------------------------------------------
async def analysis(ctx, score_data):
    #データを取得
    music_data = get_musicdata()

    #共通の曲名を持つデータを取り出す
    data = pd.merge(music_data, score_data, on=["SortNo"], how='inner')

    #不要な列を削除
    data.drop(columns=["Artist", "BPM", "Side", "Pack", "Version", "Image"], inplace=True)
    
    #PMで内部のみ書いたものをスコアに直す
    data.loc[(data["Score"] >= 1) & (data["Score"] <= 5000), "Score"] += PM
    #未記入に0点を入力
    data = data.fillna({"Score":0})
    #理論値フラグのスコア入力
    data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Score"] = data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Notes"] + PM
    data["Level"] = data["Level"].astype("str")

    analysis_datalist = []
    #各難易度ごとにデータの分析を行う
    for name, level_group in data.groupby("Level"):
        #合計点
        level_sum = level_group["Score"].sum()
        #平均点
        level_mean = round(level_group["Score"].mean())
        #PM内部失点
        level_loss_n = get_pm_loss(level_group)
        #各グレード数
        level_grade = get_grade(level_group)
        #FP
        level_fp = get_framepower(level_group)

        #データをlistに纏める
        level_analysis_list = [name, level_sum, level_mean, level_loss_n, level_grade["Max"], level_grade["PM"], level_grade["EX+"],
                               level_grade["EX"], level_grade["AA"], level_grade["Other"], level_fp["FP"], level_fp["FP_Point"], level_fp["MaxFP_Point"]]

        analysis_datalist.append(level_analysis_list)

    #全曲合計のデータ分析を行う
    data_sum = data["Score"].sum() #合計点
    data_mean = data["Score"].mean() #平均点
    data_loss_n = get_pm_loss(data) #PM内部失点
    data_grade = get_grade(data) #各グレード数
    data_fp = get_framepower(data) #FP

    #データをlistに纏める
    data_analysis_list = ["ALL", data_sum, data_mean, data_loss_n, data_grade["Max"], data_grade["PM"], data_grade["EX+"],
                           data_grade["EX"], data_grade["AA"], data_grade["Other"], data_fp["FP"], data_fp["FP_Point"], data_fp["MaxFP_Point"]]

    analysis_datalist.append(data_analysis_list)

    df = pd.DataFrame(analysis_datalist, columns=["Level", "合計点", "平均点", "PM内部失点", "理論値", "PM", "EX+", "EX", "AA", "Other", "FramePower", "FP値", "MaxFP値"])

    #データを整えてxlsxで保存
    df = df.set_index("Level",drop=False).sort_index()
    df = df.reindex(index=["7", "7+", "8", "8+", "9", "9+", "10", "10+", "11", "11+", "12", "ALL"])
    #ファイルパスの作成
    df_p_user = pd.read_csv(os.environ["P_USERLIST"])
    name = df_p_user.loc[df_p_user[df_p_user["Discord_ID"] == ctx.user.id].index, "UserName"].iloc[0]
    result_file = f"./data/score/{name}_result.xlsx"
    df.to_excel(result_file, index=False)

    #結果を送信
    await ctx.followup.send("分析が終わったよ！確認してみよう！", file=discord.File(result_file))
    #待機後、メニューを表示
    await asyncio.sleep(2)
    await start_menu(ctx, ctx.channel)


async def bestplays_50(ctx, score_data):
    """ポテンシャル上位50曲を表示"""
    # データを取得
    music_data = get_musicdata()

    # 共通の曲名を持つデータを取り出す
    data = pd.merge(music_data, score_data, on=["SortNo"], how='inner')

    # 不要な列を削除
    data.drop(columns=["Artist", "BPM", "Side", "Pack", "Version", "Image"], inplace=True)
    
    # PMで内部のみ書いたものをスコアに直す
    data.loc[(data["Score"] >= 1) & (data["Score"] <= 10000), "Score"] += PM
    # 未記入に0点を入力
    data = data.fillna({"Score":0})
    # 理論値フラグのスコア入力
    data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Score"] = data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Notes"] + PM
    data["Level"] = data["Level"].astype("str")
    
    # ポテンシャル値を計算
    result = get_potential(data)
    result.sort_values(["Potential", "SortNo"], ascending=[False, True], inplace=True)
    
    # 計算に使用するデータ抽出
    data_top10 = result.head(10)
    data_top30 = result.head(30)
    data_top50 = result.head(50)
    data_top50.reset_index(drop=True, inplace=True) # idx振りなおし
    
    pt_mean = data_top30["Potential"].mean() # best枠平均
    pt_reach = (data_top30["Potential"].sum() + data_top10["Potential"].sum()) / 40 # 到達可能ポテンシャル
    
    # メッセージ作成
    message = f"{ctx.user.display_name}さんのベスト枠Top50\n"
    
    for idx, row in data_top50.iterrows():
        if idx % 10 == 0: # 文字数制限回避の為、10の倍数で送信
            await ctx.channel.send(message) # 送信
            await asyncio.sleep(0.5)
            message = "" # メッセージ初期化
            
            if idx == 30:
                await ctx.channel.send("-----↓ベスト枠候補↓-----\n") # 送信
        #追加
        message += f"{idx+1} 「{row['Music_Title']}」\nScore：{int(row['Score']):,} Pt：{round(row['Potential'], 3)}\n"
    else:
        await ctx.channel.send(message) # 送信

    #best枠平均、到達可能pt送信
    await ctx.channel.send(
f"""
----------
Best枠平均：{round(pt_mean, 4)}
到達可能ポテンシャル：{round(pt_reach, 3)}
----------
"""
)
    
    # 待機後、メニューを表示
    await asyncio.sleep(2)
    await start_menu(ctx, ctx.channel)
    
    
async def pure_precision(ctx, score_data, level):
    """内部精度の失点数を表示する"""
    # データを取得
    music_data = get_musicdata()

    # 共通の曲名を持つデータを取り出す
    data = pd.merge(music_data, score_data, on=["SortNo"], how='inner')

    # 不要な列を削除
    data.drop(columns=["Artist", "BPM", "Side", "Pack", "Version", "Image"], inplace=True)
    
    # PMで内部のみ書いたものをスコアに直す
    data.loc[(data["Score"] >= 1) & (data["Score"] <= 10000), "Score"] += PM
    # 未記入に0点を入力
    data = data.fillna({"Score":0})
    # 理論値フラグのスコア入力
    data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Score"] = data.loc[((data["flg"] == "max") | (data["flg"] == "MAX")) & (data["Score"] == 0), "Notes"] + PM
    data["Level"] = data["Level"].astype("str")
    
    # データ抽出
    # レベル
    if level == "ALL":
        pass
    else:
        data = data[data["Level"] == level]
        
    # 未PM,理論値を除く
    data = data[(data["Score"] >= PM) & (data["Score"] != data["Notes"] + PM)]
    
    # 該当データがない場合は終了
    if data.empty:
        await ctx.channel.send("選択したレベルに該当データがないよ、メニューに戻るね。") # 送信
        # 待機後、メニューを表示
        await asyncio.sleep(2)
        return await start_menu(ctx, ctx.channel)
    
    # 内部失点計算
    result = calc_precision(data)
    result.sort_values(["Precision", "SortNo"], ascending=[False, True], inplace=True) # 内部精度でソート
    result.reset_index(drop=True, inplace=True) # idx振りなおし
    
    # メッセージ作成
    message = "----------"
    
    for idx, row in result.iterrows():
        if idx % 10 == 0: # 文字数制限回避の為、10の倍数で送信
            await ctx.channel.send(message) # 送信
            await asyncio.sleep(0.5)
            message = "" # メッセージ初期化
            
        # 追加
        message += f"{idx+1} 「{row['Music_Title']}」\nScore：{int(row['Score']):,} (Max-{int(row['Precision'])})\n"
    else:
        await ctx.channel.send(message + "----------") # 送信

    # 待機後、メニューを表示
    await asyncio.sleep(2)
    await start_menu(ctx, ctx.channel)

    
async def score_update(ctx, user):
    """スコア更新を行う"""
    #PListを取得
    df_p_user = pd.read_csv(os.environ["P_USERLIST"])


async def file_load(user):
    """ファイルデータ取得"""
    #PListを取得
    df_p_user = pd.read_csv(os.environ["P_USERLIST"])
    file_path = df_p_user.loc[df_p_user[df_p_user["Discord_ID"] == user.id].index, "Score_Path"].iloc[0]
           
    #ExcelファイルをPandasのDataFrameに変換
    df = get_mydata(file_path)

    return df


def get_musicdata():
    """楽曲情報を取得"""
    df_music = pd.read_csv(os.environ["MUSIC"])
    df_music.drop(columns=["Level", "Const"], inplace=True)
    return df_music


def get_mydata(file):
    """スコア情報を取得"""
    df_myscore = pd.read_excel(file, usecols=[1,2,3,4,5,6], skiprows=5)
    #扱いやすいように整形
    df_myscore.rename(columns={"リリース順":"SortNo", "曲名":"Music_Title", "難易度":"Level", "譜面定数":"Const", "スコア":"Score", "クリアマーク":"flg"}, inplace=True)
    df_myscore.drop(columns=["Music_Title"], inplace=True)

    return df_myscore


def get_pm_loss(data):
    """既PMの内部精度計算"""
    score_pmloss = 0
    level_pm = data[data["Score"] >= PM]
    if level_pm.empty == False:
        score_pm = sum(level_pm["Score"])
        score_pmloss = (sum(level_pm["Notes"].values) + PM*len(level_pm)) - score_pm

    return score_pmloss


def get_grade(data):
    """各グレード曲数を計算"""
    list_grade = []
    #一曲ずつ計算する
    for _, row in data.iterrows():
        score = row["Score"]
        # 理論値集計
        if score == int(row["Notes"]) + PM:
            list_grade.append("理論値")
            
        # スコアランク集計
        if score >= PM:
            list_grade.append("PM")
        elif score >= EXPLUS:
            list_grade.append("EX+")
        elif score >= EX:
            list_grade.append("EX")
        elif score >= AA:
            list_grade.append("AA")
        else:
            list_grade.append("Other")
    
    #数を集計して返す
    count_max = list_grade.count("理論値")
    count_pm = list_grade.count("PM")
    count_exp = list_grade.count("EX+") 
    count_ex = list_grade.count("EX") 
    count_aa = list_grade.count("AA") 
    count_o = list_grade.count("Other")

    #辞書に結果をまとめる
    dic_grade = {"Max":count_max, "PM":count_pm, "EX+":count_exp, "EX":count_ex, "AA":count_aa, "Other":count_o}
    return dic_grade


def get_framepower(data):
    """FramePowerを計算する"""
    #必要な情報
    max_fp_p = 0
    fp_p = 0

    #一曲ずつmaxFPとFPを計算
    for _, row in data.iterrows():
        #変数にデータを格納
        score = row["Score"]
        notes = row["Notes"]
        const = row["Const"]
        max = PM + notes

        #スコアで分岐してop計算
        if score == max:
            #理論値
            fp_p += (const + 2) + const*0.2
        elif score >= PM:
            #PM~max-1
            pure = max-score
            if pure < 100:
                #max-200~max-1
                fp_p += (const + 2) + (1-(pure*0.005))*const*0.2
            else:
                fp_p += (const + 2)
        elif score >= EX:
            #EX~1Far
                fp_p += (const + 1 + (score - EX)/200000)
        elif score >= AA:
            #AA~9,799,999
            fp_p += (const + (score - AA)/300000)
        else:
            #A以下
            fp_p += 0
        
        #曲のOP理論値を計算
        max_fp_p += (const + 2) + const*0.2

    #集計結果をまとめて返す
    fp_p = round(fp_p, 4)
    max_fp_p = round(max_fp_p, 4)
    fp = round((fp_p / max_fp_p)*100, 4)

    dic_fp = {"FP":fp, "FP_Point":fp_p, "MaxFP_Point":max_fp_p}
    return dic_fp


def get_potential(data):
    """ポテンシャル値を計算"""
    # 新規列作成
    data["Potential"] = ""
    
    for idx, row in data.iterrows():
        # スコア別ポテンシャル計算
        if row["Score"] >= PM: # PM以上
            potential = row["Const"] + 2.0
             
        elif row["Score"] >= EX: # EX以上
            potential = row["Const"] + 1.0 + (row["Score"] - EX)/200000
            
        else: # EX以下
            potential = row["Const"] + (row["Score"] - AA)/300000
            # ポテンシャルの下限は0
            if potential < 0:
                potential = 0
                
        # データ追加
        data.loc[idx, "Potential"] = potential
        
    return data


def calc_precision(data):
    """内部精度を計算"""
    # 新規列作成
    data["Precision"] = ""
    
    # 一曲ずつ内部精度を計算
    for idx, row in data.iterrows():
        # 変数にデータを格納
        score = row["Score"]
        notes = row["Notes"]
        max = PM + notes
        
        # 計算
        pure_loss = max - score
        
        # データ追加
        data.loc[idx, "Precision"] = pure_loss
        
    return data