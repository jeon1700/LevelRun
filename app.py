import serverless_wsgi    # docker

from flask import Flask
from flask_jwt_extended import JWTManager
from flask_restful import Api
from config import Config
from resources.RandomBox import RandomBoxResouce
from resources.exercise import ExcerciseListResource, ExcerciseRecordResource
from resources.gacha import GachaResource

from resources.like import LikeResource
from resources.mission import MissionInfoResource, MissionResource
from resources.posting import PostingLabelResouce, PostingListResouce, PostingPopResource, PostingResource
from resources.ranker import RankerResource, RankingListResource
from resources.user import KakaoLoginResource, UserInfoResource, UserLoginResource, UserLogoutResource, UserRegisterResource

# 로그아웃 관련된 임포트문
from resources.user import jwt_blocklist

app = Flask(__name__)

# 환경변수 셋팅
app.config.from_object(Config)
# JWT 매니저 초기화
jwt=JWTManager(app)

# # 로그아웃된 토큰으로 요청하는 경우 실행되지 않도록 처리하는 코드
@jwt.token_in_blocklist_loader
def check_if_token_is_revoked(jwt_header, jwt_payload) :
    jti = jwt_payload['jti']
    return jti in jwt_blocklist

api = Api(app)


# 경로와 리소스를 연결한다.
api.add_resource(UserRegisterResource,'/user/register') # 회원가입
api.add_resource(UserLoginResource, '/user/login')      # 로그인
api.add_resource(KakaoLoginResource, '/user/kakaoLogin')  # 카카오 로그인
api.add_resource(UserLogoutResource, '/user/logout') # 로그아웃
api.add_resource(UserInfoResource, '/user') # 유저정보

api.add_resource(PostingListResouce, '/posting') # 포스팅 생성, 전체 포스팅 가져오기
api.add_resource(PostingLabelResouce, '/posting/label') # 포스팅 라벨 생성
api.add_resource(PostingResource, '/posting/<int:postingId>') # 포스팅 상세정보, 수정, 삭제
api.add_resource(PostingPopResource, '/posting/popularity') # 포스팅 인기순 정렬

api.add_resource(LikeResource,'/like/<int:postingId>') # 좋아요 처리 / 좋아요 유무

api.add_resource(RankerResource, '/ranker') # 상위 랭커 프로필 이미지
api.add_resource(RankingListResource, '/rankingList') # 유저들의 레벨정보 가져오기

api.add_resource(RandomBoxResouce, '/box') # 랜덤상자 추가
api.add_resource(GachaResource, '/gacha') # 상자 뽑기

api.add_resource(ExcerciseRecordResource, '/excercise') # 운동 기록 저장/ 수정 / 가져오기
api.add_resource(ExcerciseListResource, '/excercise/list') # 운동 기록 리스트 가져오기

api.add_resource(MissionResource, '/mission') # 임무 완료
api.add_resource(MissionInfoResource, '/user/mission') # 임무 정보 가져오기

def handler(event, context) :
    return serverless_wsgi.handle_request(app, event, context)

if __name__ == '__main__' :
    app.run()