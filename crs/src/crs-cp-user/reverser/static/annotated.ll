; ModuleID = '/home/andrew/CRS-cp-linux/fuzzer/reverser/static/install/linux_test_harness_trans.bc'
source_filename = "../linux_test_harness.c"
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

%struct.sockaddr_in = type { i16, i16, %struct.in_addr, [8 x i8] }
%struct.in_addr = type { i32 }
%struct.sockaddr = type { i16, [14 x i8] }
%struct.sockaddr_nl = type { i16, i16, i32, i32 }
%struct.msghdr = type { i8*, i32, %struct.iovec*, i64, i8*, i64, i32 }
%struct.iovec = type { i8*, i64 }
%struct.nlmsghdr = type { i32, i16, i16, i32, i32 }
%struct.stat = type { i64, i64, i64, i32, i32, i32, i32, i64, i64, i64, i64, %struct.timespec, %struct.timespec, %struct.timespec, [3 x i64] }
%struct.timespec = type { i64, i64 }

@g_sockfd = dso_local global i32 -1, align 4, !dbg !0
@.str = private unnamed_addr constant [70 x i8] c"[INFO] Opening socket with Domain: %d Type: %d Protocol: %d Port: %d\0A\00", align 1
@g_sockaddr = dso_local global %struct.sockaddr_in zeroinitializer, align 4, !dbg !78
@.str.1 = private unnamed_addr constant [10 x i8] c"127.0.0.1\00", align 1
@.str.2 = private unnamed_addr constant [40 x i8] c"[INFO] Sending data flags: %x size: %x\0A\00", align 1
@.str.3 = private unnamed_addr constant [71 x i8] c"[INFO] Sending netlink type: %x flags: %x prot: %x seq %x pktlen: %lx\0A\00", align 1
@.str.4 = private unnamed_addr constant [7 x i8] c"socket\00", align 1
@.str.5 = private unnamed_addr constant [5 x i8] c"bind\00", align 1
@.str.6 = private unnamed_addr constant [7 x i8] c"sendto\00", align 1
@.str.7 = private unnamed_addr constant [30 x i8] c"[INFO] Executing %d commands\0A\00", align 1
@.str.8 = private unnamed_addr constant [29 x i8] c"send_netlink_packet() error\0A\00", align 1
@.str.9 = private unnamed_addr constant [29 x i8] c"[ERROR] Unknown command: %x\0A\00", align 1
@.str.10 = private unnamed_addr constant [26 x i8] c"[INFO] Sending completed\0A\00", align 1
@.str.11 = private unnamed_addr constant [11 x i8] c"Need file\0A\00", align 1
@.str.12 = private unnamed_addr constant [21 x i8] c"Failed to stat file\0A\00", align 1
@.str.13 = private unnamed_addr constant [29 x i8] c"[ERROR] Failed to open file\0A\00", align 1

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @setup_socket(i32 noundef %0, i32 noundef %1, i32 noundef %2, i16 noundef zeroext %3) #0 !dbg !110 {
  call void @llvm.dbg.value(metadata i32 %0, metadata !114, metadata !DIExpression()), !dbg !115
  call void @llvm.dbg.value(metadata i32 %1, metadata !116, metadata !DIExpression()), !dbg !115
  call void @llvm.dbg.value(metadata i32 %2, metadata !117, metadata !DIExpression()), !dbg !115
  call void @llvm.dbg.value(metadata i16 %3, metadata !118, metadata !DIExpression()), !dbg !115
  %5 = zext i16 %3 to i32, !dbg !119
  %6 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([70 x i8], [70 x i8]* @.str, i64 0, i64 0), i32 noundef %0, i32 noundef %1, i32 noundef %2, i32 noundef %5), !dbg !120
  %7 = call i32 @socket(i32 noundef %0, i32 noundef %1, i32 noundef %2) #7, !dbg !121
  store i32 %7, i32* @g_sockfd, align 4, !dbg !123
  %8 = icmp slt i32 %7, 0, !dbg !124
  br i1 %8, label %9, label %10, !dbg !125

9:                                                ; preds = %4
  store i32 -1, i32* @g_sockfd, align 4, !dbg !126
  br label %19, !dbg !128

10:                                               ; preds = %4
  call void @llvm.memset.p0i8.i64(i8* align 4 bitcast (%struct.sockaddr_in* @g_sockaddr to i8*), i8 0, i64 16, i1 false), !dbg !129
  %11 = trunc i32 %0 to i16, !dbg !130
  store i16 %11, i16* getelementptr inbounds (%struct.sockaddr_in, %struct.sockaddr_in* @g_sockaddr, i32 0, i32 0), align 4, !dbg !131
  %12 = call zeroext i16 @htons(i16 noundef zeroext %3) #8, !dbg !132
  store i16 %12, i16* getelementptr inbounds (%struct.sockaddr_in, %struct.sockaddr_in* @g_sockaddr, i32 0, i32 1), align 2, !dbg !133
  %13 = call i32 @inet_aton(i8* noundef getelementptr inbounds ([10 x i8], [10 x i8]* @.str.1, i64 0, i64 0), %struct.in_addr* noundef getelementptr inbounds (%struct.sockaddr_in, %struct.sockaddr_in* @g_sockaddr, i32 0, i32 2)) #7, !dbg !134
  %14 = icmp eq i32 %13, 0, !dbg !136
  br i1 %14, label %15, label %18, !dbg !137

15:                                               ; preds = %10
  %16 = load i32, i32* @g_sockfd, align 4, !dbg !138
  %17 = call i32 @close(i32 noundef %16), !dbg !140
  store i32 -1, i32* @g_sockfd, align 4, !dbg !141
  br label %19, !dbg !142

18:                                               ; preds = %10
  br label %19, !dbg !143

19:                                               ; preds = %18, %15, %9
  %.0 = phi i32 [ -1, %9 ], [ -1, %15 ], [ 0, %18 ], !dbg !115
  ret i32 %.0, !dbg !144
}

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare void @llvm.dbg.declare(metadata, metadata, metadata) #1

declare i32 @printf(i8* noundef, ...) #2

; Function Attrs: nounwind
declare i32 @socket(i32 noundef, i32 noundef, i32 noundef) #3

; Function Attrs: argmemonly nofree nounwind willreturn writeonly
declare void @llvm.memset.p0i8.i64(i8* nocapture writeonly, i8, i64, i1 immarg) #4

; Function Attrs: nounwind readnone willreturn
declare zeroext i16 @htons(i16 noundef zeroext) #5

; Function Attrs: nounwind
declare i32 @inet_aton(i8* noundef, %struct.in_addr* noundef) #3

declare i32 @close(i32 noundef) #2

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @send_data(i8* noundef %0, i32 noundef %1, i32 noundef %2) #0 !dbg !145 {
  call void @llvm.dbg.value(metadata i8* %0, metadata !151, metadata !DIExpression()), !dbg !152
  call void @llvm.dbg.value(metadata i32 %1, metadata !153, metadata !DIExpression()), !dbg !152
  call void @llvm.dbg.value(metadata i32 %2, metadata !154, metadata !DIExpression()), !dbg !152
  %4 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([40 x i8], [40 x i8]* @.str.2, i64 0, i64 0), i32 noundef %1, i32 noundef %2), !dbg !155
  %5 = load i32, i32* @g_sockfd, align 4, !dbg !156
  %6 = zext i32 %2 to i64, !dbg !157
  %7 = call i64 @sendto(i32 noundef %5, i8* noundef %0, i64 noundef %6, i32 noundef %1, %struct.sockaddr* noundef bitcast (%struct.sockaddr_in* @g_sockaddr to %struct.sockaddr*), i32 noundef 16), !dbg !158
  %8 = trunc i64 %7 to i32, !dbg !158
  ret i32 %8, !dbg !159
}

declare i64 @sendto(i32 noundef, i8* noundef, i64 noundef, i32 noundef, %struct.sockaddr* noundef, i32 noundef) #2

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @netlink_send(i16 noundef zeroext %0, i16 noundef zeroext %1, i32 noundef %2, i32 noundef %3, i8* noundef %4, i64 noundef %5) #0 !dbg !160 {
  %7 = alloca %struct.sockaddr_nl, align 4
  %8 = alloca %struct.msghdr, align 8
  call void @llvm.dbg.value(metadata i16 %0, metadata !166, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.value(metadata i16 %1, metadata !168, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.value(metadata i32 %2, metadata !169, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.value(metadata i32 %3, metadata !170, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.value(metadata i8* %4, metadata !171, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.value(metadata i64 %5, metadata !172, metadata !DIExpression()), !dbg !167
  call void @llvm.dbg.declare(metadata %struct.sockaddr_nl* %7, metadata !173, metadata !DIExpression()), !dbg !182
  call void @llvm.dbg.declare(metadata %struct.msghdr* %8, metadata !183, metadata !DIExpression()), !dbg !201
  %9 = zext i16 %0 to i32, !dbg !202
  %10 = zext i16 %1 to i32, !dbg !203
  %11 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([71 x i8], [71 x i8]* @.str.3, i64 0, i64 0), i32 noundef %9, i32 noundef %10, i32 noundef %2, i32 noundef %3, i64 noundef %5), !dbg !204
  %12 = bitcast %struct.msghdr* %8 to i8*, !dbg !205
  call void @llvm.memset.p0i8.i64(i8* align 8 %12, i8 0, i64 56, i1 false), !dbg !205
  %13 = bitcast %struct.sockaddr_nl* %7 to i8*, !dbg !206
  call void @llvm.memset.p0i8.i64(i8* align 4 %13, i8 0, i64 12, i1 false), !dbg !206
  %14 = getelementptr inbounds %struct.sockaddr_nl, %struct.sockaddr_nl* %7, i32 0, i32 0, !dbg !207
  store i16 16, i16* %14, align 4, !dbg !208
  %15 = add i64 16, %5, !dbg !209
  call void @llvm.dbg.value(metadata i64 %15, metadata !210, metadata !DIExpression()), !dbg !167
  %16 = call noalias i8* @malloc(i64 noundef %15) #7, !dbg !211
  call void @llvm.dbg.value(metadata i8* %16, metadata !212, metadata !DIExpression()), !dbg !167
  call void @llvm.memset.p0i8.i64(i8* align 1 %16, i8 0, i64 %15, i1 false), !dbg !213
  %17 = getelementptr inbounds i8, i8* %16, i64 16, !dbg !214
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 1 %17, i8* align 1 %4, i64 %5, i1 false), !dbg !215
  %18 = bitcast i8* %16 to %struct.nlmsghdr*, !dbg !216
  call void @llvm.dbg.value(metadata %struct.nlmsghdr* %18, metadata !217, metadata !DIExpression()), !dbg !167
  %19 = trunc i64 %15 to i32, !dbg !218
  %20 = getelementptr inbounds %struct.nlmsghdr, %struct.nlmsghdr* %18, i32 0, i32 0, !dbg !219
  store i32 %19, i32* %20, align 4, !dbg !220
  %21 = getelementptr inbounds %struct.nlmsghdr, %struct.nlmsghdr* %18, i32 0, i32 1, !dbg !221
  store i16 %0, i16* %21, align 4, !dbg !222
  %22 = getelementptr inbounds %struct.nlmsghdr, %struct.nlmsghdr* %18, i32 0, i32 2, !dbg !223
  store i16 %1, i16* %22, align 2, !dbg !224
  %23 = getelementptr inbounds %struct.nlmsghdr, %struct.nlmsghdr* %18, i32 0, i32 3, !dbg !225
  store i32 %3, i32* %23, align 4, !dbg !226
  %24 = call i32 @getpid() #7, !dbg !227
  %25 = getelementptr inbounds %struct.nlmsghdr, %struct.nlmsghdr* %18, i32 0, i32 4, !dbg !228
  store i32 %24, i32* %25, align 4, !dbg !229
  %26 = call i32 @socket(i32 noundef 16, i32 noundef 3, i32 noundef %2) #7, !dbg !230
  call void @llvm.dbg.value(metadata i32 %26, metadata !232, metadata !DIExpression()), !dbg !167
  %27 = icmp slt i32 %26, 0, !dbg !233
  br i1 %27, label %28, label %29, !dbg !234

28:                                               ; preds = %6
  call void @perror(i8* noundef getelementptr inbounds ([7 x i8], [7 x i8]* @.str.4, i64 0, i64 0)), !dbg !235
  br label %54, !dbg !237

29:                                               ; preds = %6
  %30 = bitcast %struct.sockaddr_nl* %7 to %struct.sockaddr*, !dbg !238
  %31 = call i32 @bind(i32 noundef %26, %struct.sockaddr* noundef %30, i32 noundef 12) #7, !dbg !240
  %32 = icmp slt i32 %31, 0, !dbg !241
  br i1 %32, label %33, label %34, !dbg !242

33:                                               ; preds = %29
  call void @perror(i8* noundef getelementptr inbounds ([5 x i8], [5 x i8]* @.str.5, i64 0, i64 0)), !dbg !243
  br label %54, !dbg !245

34:                                               ; preds = %29
  %35 = call i64 @sendto(i32 noundef %26, i8* noundef %16, i64 noundef %15, i32 noundef 0, %struct.sockaddr* noundef %30, i32 noundef 12), !dbg !246
  call void @llvm.dbg.value(metadata i64 %35, metadata !247, metadata !DIExpression()), !dbg !167
  %36 = icmp slt i64 %35, 0, !dbg !252
  br i1 %36, label %37, label %38, !dbg !254

37:                                               ; preds = %34
  call void @perror(i8* noundef getelementptr inbounds ([7 x i8], [7 x i8]* @.str.6, i64 0, i64 0)), !dbg !255
  br label %54, !dbg !257

38:                                               ; preds = %34
  call void @free(i8* noundef %16) #7, !dbg !258
  %39 = getelementptr inbounds %struct.msghdr, %struct.msghdr* %8, i32 0, i32 3, !dbg !259
  store i64 1, i64* %39, align 8, !dbg !260
  %40 = call noalias i8* @malloc(i64 noundef 16) #7, !dbg !261
  %41 = bitcast i8* %40 to %struct.iovec*, !dbg !261
  %42 = getelementptr inbounds %struct.msghdr, %struct.msghdr* %8, i32 0, i32 2, !dbg !262
  store %struct.iovec* %41, %struct.iovec** %42, align 8, !dbg !263
  %43 = call noalias i8* @malloc(i64 noundef 4096) #7, !dbg !264
  %44 = getelementptr inbounds %struct.iovec, %struct.iovec* %41, i32 0, i32 0, !dbg !265
  store i8* %43, i8** %44, align 8, !dbg !266
  %45 = getelementptr inbounds %struct.iovec, %struct.iovec* %41, i32 0, i32 1, !dbg !267
  store i64 4096, i64* %45, align 8, !dbg !268
  %46 = call i64 @recvmsg(i32 noundef %26, %struct.msghdr* noundef %8, i32 noundef 0), !dbg !269
  call void @llvm.dbg.value(metadata i64 %46, metadata !271, metadata !DIExpression()), !dbg !167
  br i1 false, label %47, label %49, !dbg !272

47:                                               ; preds = %38
  call void @llvm.dbg.label(metadata !273), !dbg !274
  %48 = call i32 @close(i32 noundef %26), !dbg !275
  br label %54, !dbg !276

49:                                               ; preds = %38
  %50 = load %struct.iovec*, %struct.iovec** %42, align 8, !dbg !277
  %51 = getelementptr inbounds %struct.iovec, %struct.iovec* %50, i32 0, i32 0, !dbg !278
  %52 = load i8*, i8** %51, align 8, !dbg !278
  call void @free(i8* noundef %52) #7, !dbg !279
  %53 = call i32 @close(i32 noundef %26), !dbg !280
  br label %54, !dbg !281

54:                                               ; preds = %47, %49, %37, %33, %28
  %.0 = phi i32 [ -1, %28 ], [ -1, %33 ], [ -1, %37 ], [ poison, %47 ], [ 0, %49 ], !dbg !167
  ret i32 %.0, !dbg !282
}

; Function Attrs: nounwind
declare noalias i8* @malloc(i64 noundef) #3

; Function Attrs: argmemonly nofree nounwind willreturn
declare void @llvm.memcpy.p0i8.p0i8.i64(i8* noalias nocapture writeonly, i8* noalias nocapture readonly, i64, i1 immarg) #6

; Function Attrs: nounwind
declare i32 @getpid() #3

declare void @perror(i8* noundef) #2

; Function Attrs: nounwind
declare i32 @bind(i32 noundef, %struct.sockaddr* noundef, i32 noundef) #3

; Function Attrs: nounwind
declare void @free(i8* noundef) #3

declare i64 @recvmsg(i32 noundef, %struct.msghdr* noundef, i32 noundef) #2

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare void @llvm.dbg.label(metadata) #1

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @send_netlink_packet(i8* noundef %0, i32 noundef %1) #0 !dbg !283 {
  %3 = alloca i32, align 4
  %4 = alloca i32, align 4
  %5 = alloca i32, align 4
  %6 = alloca i32, align 4
  call void @llvm.dbg.value(metadata i8* %0, metadata !286, metadata !DIExpression()), !dbg !287
  call void @llvm.dbg.value(metadata i32 %1, metadata !288, metadata !DIExpression()), !dbg !287
  call void @llvm.dbg.value(metadata i32 0, metadata !289, metadata !DIExpression()), !dbg !287
  call void @llvm.dbg.declare(metadata i32* %3, metadata !290, metadata !DIExpression()), !dbg !291
  store i32 0, i32* %3, align 4, !dbg !291
  call void @llvm.dbg.declare(metadata i32* %4, metadata !292, metadata !DIExpression()), !dbg !293
  call void @llvm.dbg.declare(metadata i32* %5, metadata !294, metadata !DIExpression()), !dbg !295
  call void @llvm.dbg.declare(metadata i32* %6, metadata !296, metadata !DIExpression()), !dbg !297
  %7 = icmp eq i8* %0, null, !dbg !298
  br i1 %7, label %8, label %9, !dbg !300

8:                                                ; preds = %2
  br label %40, !dbg !301

9:                                                ; preds = %2
  %10 = icmp ult i32 %1, 16, !dbg !303
  br i1 %10, label %11, label %12, !dbg !305

11:                                               ; preds = %9
  br label %40, !dbg !306

12:                                               ; preds = %9
  %13 = bitcast i32* %4 to i8*, !dbg !308
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %13, i8* align 1 %0, i64 4, i1 false), !dbg !308
  %14 = bitcast i32* %5 to i8*, !dbg !309
  %15 = getelementptr inbounds i8, i8* %0, i64 4, !dbg !310
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %14, i8* align 1 %15, i64 4, i1 false), !dbg !309
  %16 = bitcast i32* %6 to i8*, !dbg !311
  %17 = getelementptr inbounds i8, i8* %0, i64 8, !dbg !312
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %16, i8* align 1 %17, i64 4, i1 false), !dbg !311
  %18 = bitcast i32* %3 to i8*, !dbg !313
  %19 = getelementptr inbounds i8, i8* %0, i64 12, !dbg !314
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %18, i8* align 1 %19, i64 4, i1 false), !dbg !313
  call void @llvm.dbg.value(metadata i32 16, metadata !289, metadata !DIExpression()), !dbg !287
  %20 = sub i32 %1, 16, !dbg !315
  %21 = load i32, i32* %3, align 4, !dbg !317
  %22 = icmp ult i32 %20, %21, !dbg !318
  br i1 %22, label %23, label %24, !dbg !319

23:                                               ; preds = %12
  br label %40, !dbg !320

24:                                               ; preds = %12
  %25 = load i32, i32* %4, align 4, !dbg !322
  %26 = trunc i32 %25 to i16, !dbg !322
  %27 = load i32, i32* %5, align 4, !dbg !324
  %28 = trunc i32 %27 to i16, !dbg !324
  %29 = load i32, i32* %6, align 4, !dbg !325
  %30 = call i64 @time(i64* noundef null) #7, !dbg !326
  %31 = trunc i64 %30 to i32, !dbg !326
  %32 = getelementptr inbounds i8, i8* %0, i64 16, !dbg !327
  %33 = zext i32 %21 to i64, !dbg !328
  %34 = call i32 @netlink_send(i16 noundef zeroext %26, i16 noundef zeroext %28, i32 noundef %29, i32 noundef %31, i8* noundef %32, i64 noundef %33), !dbg !329
  %35 = icmp slt i32 %34, 0, !dbg !330
  br i1 %35, label %36, label %37, !dbg !331

36:                                               ; preds = %24
  br label %40, !dbg !332

37:                                               ; preds = %24
  %38 = add i32 16, %21, !dbg !334
  call void @llvm.dbg.value(metadata i32 %38, metadata !289, metadata !DIExpression()), !dbg !287
  %39 = call i32 @sleep(i32 noundef 2), !dbg !335
  br label %40, !dbg !336

40:                                               ; preds = %37, %36, %23, %11, %8
  %.0 = phi i32 [ -1, %8 ], [ -1, %11 ], [ -1, %23 ], [ -1, %36 ], [ %38, %37 ], !dbg !287
  ret i32 %.0, !dbg !337
}

; Function Attrs: nounwind
declare i64 @time(i64* noundef) #3

declare i32 @sleep(i32 noundef) #2

; Function Attrs: noinline nounwind uwtable
; ANDREW %0 is blob
define dso_local i32 @harness(i8* noundef %0, i32 noundef %1) #0 !dbg !338 {
  %3 = alloca i32, align 4
  %4 = alloca i32, align 4
  %5 = alloca i32, align 4
  %6 = alloca i32, align 4
  call void @llvm.dbg.value(metadata i8* %0, metadata !339, metadata !DIExpression()), !dbg !340
  call void @llvm.dbg.value(metadata i32 %1, metadata !341, metadata !DIExpression()), !dbg !340
  call void @llvm.dbg.value(metadata i32 0, metadata !342, metadata !DIExpression()), !dbg !340
  call void @llvm.dbg.declare(metadata i32* %3, metadata !343, metadata !DIExpression()), !dbg !344
  call void @llvm.dbg.declare(metadata i32* %4, metadata !345, metadata !DIExpression()), !dbg !346
  store i32 0, i32* %4, align 4, !dbg !346
  call void @llvm.dbg.declare(metadata i32* %5, metadata !347, metadata !DIExpression()), !dbg !348
  call void @llvm.dbg.declare(metadata i32* %6, metadata !349, metadata !DIExpression()), !dbg !350
  store i32 0, i32* %6, align 4, !dbg !350
  call void @llvm.dbg.declare(metadata i32* undef, metadata !351, metadata !DIExpression()), !dbg !352
  call void @llvm.dbg.declare(metadata i32* undef, metadata !353, metadata !DIExpression()), !dbg !354
  call void @llvm.dbg.declare(metadata i32* undef, metadata !355, metadata !DIExpression()), !dbg !356
  call void @llvm.dbg.declare(metadata i16* undef, metadata !357, metadata !DIExpression()), !dbg !358
  call void @llvm.dbg.declare(metadata i32* undef, metadata !359, metadata !DIExpression()), !dbg !360
  call void @llvm.dbg.declare(metadata i32* undef, metadata !361, metadata !DIExpression()), !dbg !362
  call void @llvm.dbg.declare(metadata i32* undef, metadata !363, metadata !DIExpression()), !dbg !364
  %7 = icmp eq i8* %0, null, !dbg !365
  br i1 %7, label %8, label %9, !dbg !367

8:                                                ; preds = %2
  br label %80, !dbg !368

9:                                                ; preds = %2
  %10 = call i32 @setup_socket(i32 noundef 2, i32 noundef 2, i32 noundef 17, i16 noundef zeroext 6118), !dbg !370
  %11 = icmp slt i32 %10, 0, !dbg !372
  br i1 %11, label %12, label %13, !dbg !373

12:                                               ; preds = %9
  br label %80, !dbg !374

13:                                               ; preds = %9
  %14 = icmp ult i32 %1, 4, !dbg !376
  br i1 %14, label %15, label %16, !dbg !378

15:                                               ; preds = %13
  br label %80, !dbg !379

16:                                               ; preds = %13
  %17 = bitcast i32* %4 to i8*, !dbg !381
  ; ANDREW line 201, memcpy into command_count (%17 = %4)
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %17, i8* align 1 %0, i64 4, i1 false), !dbg !381
  call void @llvm.dbg.value(metadata i32 4, metadata !342, metadata !DIExpression()), !dbg !340
  %18 = load i32, i32* %4, align 4, !dbg !382
  %19 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([30 x i8], [30 x i8]* @.str.7, i64 0, i64 0), i32 noundef %18), !dbg !383
  call void @llvm.dbg.value(metadata i32 0, metadata !384, metadata !DIExpression()), !dbg !386
  br label %20, !dbg !387

20:                                               ; preds = %74, %16
  ; ANDREW %.02 is index, compiler smart enough to initialize as 4
  %.02 = phi i32 [ 4, %16 ], [ %.1, %74 ], !dbg !340
  %.01 = phi i32 [ 0, %16 ], [ %75, %74 ], !dbg !386
  call void @llvm.dbg.value(metadata i32 %.01, metadata !384, metadata !DIExpression()), !dbg !386
  call void @llvm.dbg.value(metadata i32 %.02, metadata !342, metadata !DIExpression()), !dbg !340
  %21 = icmp ult i32 %.01, %18, !dbg !388
  br i1 %21, label %22, label %76, !dbg !390

22:                                               ; preds = %20
  %23 = sub i32 %1, %.02, !dbg !391
  %24 = icmp ult i32 %23, 4, !dbg !394
  br i1 %24, label %25, label %26, !dbg !395

25:                                               ; preds = %22
  br label %80, !dbg !396

26:                                               ; preds = %22
  %27 = bitcast i32* %3 to i8*, !dbg !398
  %28 = sext i32 %.02 to i64, !dbg !399
  ; ANDREW Get blob (%0) at index (%28 = %.02)
  %29 = getelementptr inbounds i8, i8* %0, i64 %28, !dbg !399
  ; ANDREW store blob + index at command (%27 = %3)
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %27, i8* align 1 %29, i64 4, i1 false), !dbg !398
  ; ANDREW add 4 to index (%.02)
  %30 = add nsw i32 %.02, 4, !dbg !400
  call void @llvm.dbg.value(metadata i32 %30, metadata !342, metadata !DIExpression()), !dbg !340
  %31 = load i32, i32* %3, align 4, !dbg !401
  ; ANDREW switch on command (%31 = %3). Make sure %3 wasn't written to between memcpy and load.
  switch i32 %31, label %72 [
    i32 0, label %32
    i32 1, label %62
  ], !dbg !402

32:                                               ; preds = %26
  %33 = sub i32 %1, %30, !dbg !403
  %34 = icmp ult i32 %33, 8, !dbg !406
  br i1 %34, label %35, label %38, !dbg !407

35:                                               ; preds = %32
  %36 = load i32, i32* @g_sockfd, align 4, !dbg !408
  %37 = call i32 @close(i32 noundef %36), !dbg !410
  br label %80, !dbg !411

38:                                               ; preds = %32
  %39 = bitcast i32* %6 to i8*, !dbg !412
  %40 = sext i32 %30 to i64, !dbg !413
  ; ANDREW Get blob at index (now in %30 after adding)
  %41 = getelementptr inbounds i8, i8* %0, i64 %40, !dbg !413
  ; ANDREW memcpy into packet_size (%39 = %6)
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %39, i8* align 1 %41, i64 4, i1 false), !dbg !412
  %42 = bitcast i32* %5 to i8*, !dbg !414
  ; ANDREW get the previous blob + index (%41) plus another 4
  %43 = getelementptr inbounds i8, i8* %41, i64 4, !dbg !415
  ; ANDREW memcpy into flags (%42 = %5)
  call void @llvm.memcpy.p0i8.p0i8.i64(i8* align 4 %42, i8* align 1 %43, i64 4, i1 false), !dbg !414
  ; ANDREW add 8 to index (%30 + 8 into %44)
  %44 = add nsw i32 %30, 8, !dbg !416
  call void @llvm.dbg.value(metadata i32 %44, metadata !342, metadata !DIExpression()), !dbg !340
  %45 = sub i32 %1, %44, !dbg !417
  %46 = load i32, i32* %6, align 4, !dbg !419
  %47 = icmp ult i32 %45, %46, !dbg !420
  br i1 %47, label %48, label %51, !dbg !421

48:                                               ; preds = %38
  %49 = load i32, i32* @g_sockfd, align 4, !dbg !422
  %50 = call i32 @close(i32 noundef %49), !dbg !424
  br label %80, !dbg !425

51:                                               ; preds = %38
  %52 = sext i32 %44 to i64, !dbg !426
  ; ANDREW get blob + index (%52 = %44)
  %53 = getelementptr inbounds i8, i8* %0, i64 %52, !dbg !426
  %54 = load i32, i32* %5, align 4, !dbg !428
  ; ANDREW call send_data on blob + index (%52)
  %55 = call i32 @send_data(i8* noundef %53, i32 noundef %54, i32 noundef %46), !dbg !429
  %56 = icmp slt i32 %55, 0, !dbg !430
  br i1 %56, label %57, label %60, !dbg !431

57:                                               ; preds = %51
  %58 = load i32, i32* @g_sockfd, align 4, !dbg !432
  %59 = call i32 @close(i32 noundef %58), !dbg !434
  br label %80, !dbg !435

60:                                               ; preds = %51
  ; ANDREW increment index (%44) by packet_size (%46 = %6)
  %61 = add i32 %44, %46, !dbg !436
  call void @llvm.dbg.value(metadata i32 %61, metadata !342, metadata !DIExpression()), !dbg !340
  br label %74, !dbg !437

62:                                               ; preds = %26
  %63 = sext i32 %30 to i64, !dbg !438
  ; ANDREW get blob + index (%30)
  %64 = getelementptr inbounds i8, i8* %0, i64 %63, !dbg !438
  ; ANDREW blob_size (%1) minus index (%30)
  %65 = sub i32 %1, %30, !dbg !439
  %66 = call i32 @send_netlink_packet(i8* noundef %64, i32 noundef %65), !dbg !440
  call void @llvm.dbg.value(metadata i32 %66, metadata !441, metadata !DIExpression()), !dbg !340
  %67 = icmp slt i32 %66, 0, !dbg !442
  br i1 %67, label %68, label %70, !dbg !444

68:                                               ; preds = %62
  %69 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([29 x i8], [29 x i8]* @.str.8, i64 0, i64 0)), !dbg !445
  br label %80, !dbg !447

70:                                               ; preds = %62
  ; ANDREW index, add result (%30)
  %71 = add nsw i32 %30, %66, !dbg !448
  call void @llvm.dbg.value(metadata i32 %71, metadata !342, metadata !DIExpression()), !dbg !340
  br label %74, !dbg !449

72:                                               ; preds = %26
  %73 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([29 x i8], [29 x i8]* @.str.9, i64 0, i64 0), i32 noundef %31), !dbg !450
  br label %80, !dbg !451

74:                                               ; preds = %70, %60
  ; ANDREW merge index
  %.1 = phi i32 [ %71, %70 ], [ %61, %60 ], !dbg !452
  call void @llvm.dbg.value(metadata i32 %.1, metadata !342, metadata !DIExpression()), !dbg !340
  %75 = add nsw i32 %.01, 1, !dbg !453
  call void @llvm.dbg.value(metadata i32 %75, metadata !384, metadata !DIExpression()), !dbg !386
  br label %20, !dbg !454, !llvm.loop !455

76:                                               ; preds = %20
  %77 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([26 x i8], [26 x i8]* @.str.10, i64 0, i64 0)), !dbg !458
  %78 = load i32, i32* @g_sockfd, align 4, !dbg !459
  %79 = call i32 @close(i32 noundef %78), !dbg !460
  br label %80, !dbg !461

80:                                               ; preds = %76, %72, %68, %57, %48, %35, %25, %15, %12, %8
  ret i32 -1, !dbg !462
}

; Function Attrs: noinline nounwind uwtable
define dso_local i32 @main(i32 noundef %0, i8** noundef %1) #0 !dbg !463 {
  %3 = alloca %struct.stat, align 8
  call void @llvm.dbg.value(metadata i32 %0, metadata !467, metadata !DIExpression()), !dbg !468
  call void @llvm.dbg.value(metadata i8** %1, metadata !469, metadata !DIExpression()), !dbg !468
  call void @llvm.dbg.value(metadata i8* null, metadata !470, metadata !DIExpression()), !dbg !468
  call void @llvm.dbg.declare(metadata %struct.stat* %3, metadata !471, metadata !DIExpression()), !dbg !509
  %4 = icmp slt i32 %0, 2, !dbg !510
  br i1 %4, label %5, label %7, !dbg !512

5:                                                ; preds = %2
  %6 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([11 x i8], [11 x i8]* @.str.11, i64 0, i64 0)), !dbg !513
  br label %32, !dbg !515

7:                                                ; preds = %2
  %8 = getelementptr inbounds i8*, i8** %1, i64 1, !dbg !516
  %9 = load i8*, i8** %8, align 8, !dbg !516
  %10 = call i32 @stat(i8* noundef %9, %struct.stat* noundef %3) #7, !dbg !518
  %11 = icmp ne i32 %10, 0, !dbg !519
  br i1 %11, label %12, label %14, !dbg !520

12:                                               ; preds = %7
  %13 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([21 x i8], [21 x i8]* @.str.12, i64 0, i64 0)), !dbg !521
  br label %32, !dbg !523

14:                                               ; preds = %7
  %15 = load i8*, i8** %8, align 8, !dbg !524
  %16 = call i32 (i8*, i32, ...) @open(i8* noundef %15, i32 noundef 0), !dbg !525
  call void @llvm.dbg.value(metadata i32 %16, metadata !526, metadata !DIExpression()), !dbg !468
  %17 = icmp slt i32 %16, 0, !dbg !527
  br i1 %17, label %18, label %20, !dbg !529

18:                                               ; preds = %14
  %19 = call i32 (i8*, ...) @printf(i8* noundef getelementptr inbounds ([29 x i8], [29 x i8]* @.str.13, i64 0, i64 0)), !dbg !530
  br label %32, !dbg !532

20:                                               ; preds = %14
  %21 = getelementptr inbounds %struct.stat, %struct.stat* %3, i32 0, i32 8, !dbg !533
  %22 = load i64, i64* %21, align 8, !dbg !533
  %23 = call noalias i8* @malloc(i64 noundef %22) #7, !dbg !534
  call void @llvm.dbg.value(metadata i8* %23, metadata !470, metadata !DIExpression()), !dbg !468
  %24 = icmp eq i8* %23, null, !dbg !535
  br i1 %24, label %25, label %26, !dbg !537

25:                                               ; preds = %20
  br label %32, !dbg !538

26:                                               ; preds = %20
  %27 = call i64 @read(i32 noundef %16, i8* noundef %23, i64 noundef %22), !dbg !540
  %28 = call i32 @close(i32 noundef %16), !dbg !541
  %29 = load i64, i64* %21, align 8, !dbg !542
  %30 = trunc i64 %29 to i32, !dbg !543
  %31 = call i32 @harness(i8* noundef %23, i32 noundef %30), !dbg !544
  br label %32, !dbg !545

32:                                               ; preds = %26, %25, %18, %12, %5
  %.0 = phi i32 [ -1, %5 ], [ -1, %12 ], [ -1, %18 ], [ 0, %25 ], [ 0, %26 ], !dbg !468
  ret i32 %.0, !dbg !546
}

; Function Attrs: nounwind
declare i32 @stat(i8* noundef, %struct.stat* noundef) #3

declare i32 @open(i8* noundef, i32 noundef, ...) #2

declare i64 @read(i32 noundef, i8* noundef, i64 noundef) #2

; Function Attrs: nofree nosync nounwind readnone speculatable willreturn
declare void @llvm.dbg.value(metadata, metadata, metadata) #1

attributes #0 = { noinline nounwind uwtable "frame-pointer"="all" "min-legal-vector-width"="0" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #1 = { nofree nosync nounwind readnone speculatable willreturn }
attributes #2 = { "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #3 = { nounwind "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #4 = { argmemonly nofree nounwind willreturn writeonly }
attributes #5 = { nounwind readnone willreturn "frame-pointer"="all" "no-trapping-math"="true" "stack-protector-buffer-size"="8" "target-cpu"="x86-64" "target-features"="+cx8,+fxsr,+mmx,+sse,+sse2,+x87" "tune-cpu"="generic" }
attributes #6 = { argmemonly nofree nounwind willreturn }
attributes #7 = { nounwind }
attributes #8 = { nounwind readnone willreturn }

!llvm.dbg.cu = !{!2}
!llvm.module.flags = !{!102, !103, !104, !105, !106, !107, !108}
!llvm.ident = !{!109}

!0 = !DIGlobalVariableExpression(var: !1, expr: !DIExpression())
!1 = distinct !DIGlobalVariable(name: "g_sockfd", scope: !2, file: !3, line: 16, type: !101, isLocal: false, isDefinition: true)
!2 = distinct !DICompileUnit(language: DW_LANG_C99, file: !3, producer: "Ubuntu clang version 14.0.0-1ubuntu1.1", isOptimized: false, runtimeVersion: 0, emissionKind: FullDebug, enums: !4, retainedTypes: !49, globals: !77, splitDebugInlining: false, nameTableKind: None)
!3 = !DIFile(filename: "../linux_test_harness.c", directory: "/home/andrew/CRS-cp-linux/fuzzer/reverser/static/install", checksumkind: CSK_MD5, checksum: "4e10f0810af3d9b9b995ab32ba04dc03")
!4 = !{!5, !18}
!5 = !DICompositeType(tag: DW_TAG_enumeration_type, name: "__socket_type", file: !6, line: 24, baseType: !7, size: 32, elements: !8)
!6 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/socket_type.h", directory: "", checksumkind: CSK_MD5, checksum: "0d4e972fdeb3da9a5bc94fa41144e9f8")
!7 = !DIBasicType(name: "unsigned int", size: 32, encoding: DW_ATE_unsigned)
!8 = !{!9, !10, !11, !12, !13, !14, !15, !16, !17}
!9 = !DIEnumerator(name: "SOCK_STREAM", value: 1)
!10 = !DIEnumerator(name: "SOCK_DGRAM", value: 2)
!11 = !DIEnumerator(name: "SOCK_RAW", value: 3)
!12 = !DIEnumerator(name: "SOCK_RDM", value: 4)
!13 = !DIEnumerator(name: "SOCK_SEQPACKET", value: 5)
!14 = !DIEnumerator(name: "SOCK_DCCP", value: 6)
!15 = !DIEnumerator(name: "SOCK_PACKET", value: 10)
!16 = !DIEnumerator(name: "SOCK_CLOEXEC", value: 524288)
!17 = !DIEnumerator(name: "SOCK_NONBLOCK", value: 2048)
!18 = !DICompositeType(tag: DW_TAG_enumeration_type, file: !19, line: 40, baseType: !7, size: 32, elements: !20)
!19 = !DIFile(filename: "/usr/include/netinet/in.h", directory: "", checksumkind: CSK_MD5, checksum: "eb6560f10d4cfe9f30fea2c92b9da0fd")
!20 = !{!21, !22, !23, !24, !25, !26, !27, !28, !29, !30, !31, !32, !33, !34, !35, !36, !37, !38, !39, !40, !41, !42, !43, !44, !45, !46, !47, !48}
!21 = !DIEnumerator(name: "IPPROTO_IP", value: 0)
!22 = !DIEnumerator(name: "IPPROTO_ICMP", value: 1)
!23 = !DIEnumerator(name: "IPPROTO_IGMP", value: 2)
!24 = !DIEnumerator(name: "IPPROTO_IPIP", value: 4)
!25 = !DIEnumerator(name: "IPPROTO_TCP", value: 6)
!26 = !DIEnumerator(name: "IPPROTO_EGP", value: 8)
!27 = !DIEnumerator(name: "IPPROTO_PUP", value: 12)
!28 = !DIEnumerator(name: "IPPROTO_UDP", value: 17)
!29 = !DIEnumerator(name: "IPPROTO_IDP", value: 22)
!30 = !DIEnumerator(name: "IPPROTO_TP", value: 29)
!31 = !DIEnumerator(name: "IPPROTO_DCCP", value: 33)
!32 = !DIEnumerator(name: "IPPROTO_IPV6", value: 41)
!33 = !DIEnumerator(name: "IPPROTO_RSVP", value: 46)
!34 = !DIEnumerator(name: "IPPROTO_GRE", value: 47)
!35 = !DIEnumerator(name: "IPPROTO_ESP", value: 50)
!36 = !DIEnumerator(name: "IPPROTO_AH", value: 51)
!37 = !DIEnumerator(name: "IPPROTO_MTP", value: 92)
!38 = !DIEnumerator(name: "IPPROTO_BEETPH", value: 94)
!39 = !DIEnumerator(name: "IPPROTO_ENCAP", value: 98)
!40 = !DIEnumerator(name: "IPPROTO_PIM", value: 103)
!41 = !DIEnumerator(name: "IPPROTO_COMP", value: 108)
!42 = !DIEnumerator(name: "IPPROTO_SCTP", value: 132)
!43 = !DIEnumerator(name: "IPPROTO_UDPLITE", value: 136)
!44 = !DIEnumerator(name: "IPPROTO_MPLS", value: 137)
!45 = !DIEnumerator(name: "IPPROTO_ETHERNET", value: 143)
!46 = !DIEnumerator(name: "IPPROTO_RAW", value: 255)
!47 = !DIEnumerator(name: "IPPROTO_MPTCP", value: 262)
!48 = !DIEnumerator(name: "IPPROTO_MAX", value: 263)
!49 = !{!50, !52, !64, !76}
!50 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !51, size: 64)
!51 = !DIBasicType(name: "char", size: 8, encoding: DW_ATE_signed_char)
!52 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !53, size: 64)
!53 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "sockaddr", file: !54, line: 180, size: 128, elements: !55)
!54 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/socket.h", directory: "", checksumkind: CSK_MD5, checksum: "e3826be048699664d9ef7b080f62f2e0")
!55 = !{!56, !60}
!56 = !DIDerivedType(tag: DW_TAG_member, name: "sa_family", scope: !53, file: !54, line: 182, baseType: !57, size: 16)
!57 = !DIDerivedType(tag: DW_TAG_typedef, name: "sa_family_t", file: !58, line: 28, baseType: !59)
!58 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/sockaddr.h", directory: "", checksumkind: CSK_MD5, checksum: "dd7f1d9dd6e26f88d1726905ed5d9ff5")
!59 = !DIBasicType(name: "unsigned short", size: 16, encoding: DW_ATE_unsigned)
!60 = !DIDerivedType(tag: DW_TAG_member, name: "sa_data", scope: !53, file: !54, line: 183, baseType: !61, size: 112, offset: 16)
!61 = !DICompositeType(tag: DW_TAG_array_type, baseType: !51, size: 112, elements: !62)
!62 = !{!63}
!63 = !DISubrange(count: 14)
!64 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !65, size: 64)
!65 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "nlmsghdr", file: !66, line: 44, size: 128, elements: !67)
!66 = !DIFile(filename: "/usr/include/linux/netlink.h", directory: "", checksumkind: CSK_MD5, checksum: "a4d48e794ad1f1a951d9d1346a774e2b")
!67 = !{!68, !71, !73, !74, !75}
!68 = !DIDerivedType(tag: DW_TAG_member, name: "nlmsg_len", scope: !65, file: !66, line: 45, baseType: !69, size: 32)
!69 = !DIDerivedType(tag: DW_TAG_typedef, name: "__u32", file: !70, line: 27, baseType: !7)
!70 = !DIFile(filename: "/usr/include/asm-generic/int-ll64.h", directory: "", checksumkind: CSK_MD5, checksum: "b810f270733e106319b67ef512c6246e")
!71 = !DIDerivedType(tag: DW_TAG_member, name: "nlmsg_type", scope: !65, file: !66, line: 46, baseType: !72, size: 16, offset: 32)
!72 = !DIDerivedType(tag: DW_TAG_typedef, name: "__u16", file: !70, line: 24, baseType: !59)
!73 = !DIDerivedType(tag: DW_TAG_member, name: "nlmsg_flags", scope: !65, file: !66, line: 47, baseType: !72, size: 16, offset: 48)
!74 = !DIDerivedType(tag: DW_TAG_member, name: "nlmsg_seq", scope: !65, file: !66, line: 48, baseType: !69, size: 32, offset: 64)
!75 = !DIDerivedType(tag: DW_TAG_member, name: "nlmsg_pid", scope: !65, file: !66, line: 49, baseType: !69, size: 32, offset: 96)
!76 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: null, size: 64)
!77 = !{!0, !78}
!78 = !DIGlobalVariableExpression(var: !79, expr: !DIExpression())
!79 = distinct !DIGlobalVariable(name: "g_sockaddr", scope: !2, file: !3, line: 17, type: !80, isLocal: false, isDefinition: true)
!80 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "sockaddr_in", file: !19, line: 245, size: 128, elements: !81)
!81 = !{!82, !83, !89, !96}
!82 = !DIDerivedType(tag: DW_TAG_member, name: "sin_family", scope: !80, file: !19, line: 247, baseType: !57, size: 16)
!83 = !DIDerivedType(tag: DW_TAG_member, name: "sin_port", scope: !80, file: !19, line: 248, baseType: !84, size: 16, offset: 16)
!84 = !DIDerivedType(tag: DW_TAG_typedef, name: "in_port_t", file: !19, line: 123, baseType: !85)
!85 = !DIDerivedType(tag: DW_TAG_typedef, name: "uint16_t", file: !86, line: 25, baseType: !87)
!86 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/stdint-uintn.h", directory: "", checksumkind: CSK_MD5, checksum: "2bf2ae53c58c01b1a1b9383b5195125c")
!87 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uint16_t", file: !88, line: 40, baseType: !59)
!88 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/types.h", directory: "", checksumkind: CSK_MD5, checksum: "d108b5f93a74c50510d7d9bc0ab36df9")
!89 = !DIDerivedType(tag: DW_TAG_member, name: "sin_addr", scope: !80, file: !19, line: 249, baseType: !90, size: 32, offset: 32)
!90 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "in_addr", file: !19, line: 31, size: 32, elements: !91)
!91 = !{!92}
!92 = !DIDerivedType(tag: DW_TAG_member, name: "s_addr", scope: !90, file: !19, line: 33, baseType: !93, size: 32)
!93 = !DIDerivedType(tag: DW_TAG_typedef, name: "in_addr_t", file: !19, line: 30, baseType: !94)
!94 = !DIDerivedType(tag: DW_TAG_typedef, name: "uint32_t", file: !86, line: 26, baseType: !95)
!95 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uint32_t", file: !88, line: 42, baseType: !7)
!96 = !DIDerivedType(tag: DW_TAG_member, name: "sin_zero", scope: !80, file: !19, line: 252, baseType: !97, size: 64, offset: 64)
!97 = !DICompositeType(tag: DW_TAG_array_type, baseType: !98, size: 64, elements: !99)
!98 = !DIBasicType(name: "unsigned char", size: 8, encoding: DW_ATE_unsigned_char)
!99 = !{!100}
!100 = !DISubrange(count: 8)
!101 = !DIBasicType(name: "int", size: 32, encoding: DW_ATE_signed)
!102 = !{i32 7, !"Dwarf Version", i32 5}
!103 = !{i32 2, !"Debug Info Version", i32 3}
!104 = !{i32 1, !"wchar_size", i32 4}
!105 = !{i32 7, !"PIC Level", i32 2}
!106 = !{i32 7, !"PIE Level", i32 2}
!107 = !{i32 7, !"uwtable", i32 1}
!108 = !{i32 7, !"frame-pointer", i32 2}
!109 = !{!"Ubuntu clang version 14.0.0-1ubuntu1.1"}
!110 = distinct !DISubprogram(name: "setup_socket", scope: !3, file: !3, line: 19, type: !111, scopeLine: 20, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!111 = !DISubroutineType(types: !112)
!112 = !{!101, !94, !94, !94, !85}
!113 = !{}
!114 = !DILocalVariable(name: "domain", arg: 1, scope: !110, file: !3, line: 19, type: !94)
!115 = !DILocation(line: 0, scope: !110)
!116 = !DILocalVariable(name: "type", arg: 2, scope: !110, file: !3, line: 19, type: !94)
!117 = !DILocalVariable(name: "protocol", arg: 3, scope: !110, file: !3, line: 19, type: !94)
!118 = !DILocalVariable(name: "port", arg: 4, scope: !110, file: !3, line: 19, type: !85)
!119 = !DILocation(line: 22, column: 33, scope: !110)
!120 = !DILocation(line: 21, column: 5, scope: !110)
!121 = !DILocation(line: 24, column: 21, scope: !122)
!122 = distinct !DILexicalBlock(scope: !110, file: !3, line: 24, column: 9)
!123 = !DILocation(line: 24, column: 19, scope: !122)
!124 = !DILocation(line: 24, column: 53, scope: !122)
!125 = !DILocation(line: 24, column: 9, scope: !110)
!126 = !DILocation(line: 25, column: 18, scope: !127)
!127 = distinct !DILexicalBlock(scope: !122, file: !3, line: 24, column: 58)
!128 = !DILocation(line: 26, column: 9, scope: !127)
!129 = !DILocation(line: 29, column: 5, scope: !110)
!130 = !DILocation(line: 30, column: 29, scope: !110)
!131 = !DILocation(line: 30, column: 27, scope: !110)
!132 = !DILocation(line: 31, column: 27, scope: !110)
!133 = !DILocation(line: 31, column: 25, scope: !110)
!134 = !DILocation(line: 33, column: 9, scope: !135)
!135 = distinct !DILexicalBlock(scope: !110, file: !3, line: 33, column: 9)
!136 = !DILocation(line: 33, column: 54, scope: !135)
!137 = !DILocation(line: 33, column: 9, scope: !110)
!138 = !DILocation(line: 34, column: 15, scope: !139)
!139 = distinct !DILexicalBlock(scope: !135, file: !3, line: 33, column: 60)
!140 = !DILocation(line: 34, column: 9, scope: !139)
!141 = !DILocation(line: 35, column: 18, scope: !139)
!142 = !DILocation(line: 37, column: 9, scope: !139)
!143 = !DILocation(line: 41, column: 5, scope: !110)
!144 = !DILocation(line: 42, column: 1, scope: !110)
!145 = distinct !DISubprogram(name: "send_data", scope: !3, file: !3, line: 44, type: !146, scopeLine: 45, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!146 = !DISubroutineType(types: !147)
!147 = !{!101, !148, !94, !94}
!148 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !149, size: 64)
!149 = !DIDerivedType(tag: DW_TAG_typedef, name: "uint8_t", file: !86, line: 24, baseType: !150)
!150 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uint8_t", file: !88, line: 38, baseType: !98)
!151 = !DILocalVariable(name: "buf", arg: 1, scope: !145, file: !3, line: 44, type: !148)
!152 = !DILocation(line: 0, scope: !145)
!153 = !DILocalVariable(name: "flags", arg: 2, scope: !145, file: !3, line: 44, type: !94)
!154 = !DILocalVariable(name: "sz", arg: 3, scope: !145, file: !3, line: 44, type: !94)
!155 = !DILocation(line: 46, column: 5, scope: !145)
!156 = !DILocation(line: 48, column: 20, scope: !145)
!157 = !DILocation(line: 48, column: 35, scope: !145)
!158 = !DILocation(line: 48, column: 12, scope: !145)
!159 = !DILocation(line: 48, column: 5, scope: !145)
!160 = distinct !DISubprogram(name: "netlink_send", scope: !3, file: !3, line: 52, type: !161, scopeLine: 53, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!161 = !DISubroutineType(types: !162)
!162 = !{!101, !85, !85, !94, !94, !148, !163}
!163 = !DIDerivedType(tag: DW_TAG_typedef, name: "size_t", file: !164, line: 46, baseType: !165)
!164 = !DIFile(filename: "/usr/lib/llvm-14/lib/clang/14.0.0/include/stddef.h", directory: "", checksumkind: CSK_MD5, checksum: "2499dd2361b915724b073282bea3a7bc")
!165 = !DIBasicType(name: "unsigned long", size: 64, encoding: DW_ATE_unsigned)
!166 = !DILocalVariable(name: "type", arg: 1, scope: !160, file: !3, line: 52, type: !85)
!167 = !DILocation(line: 0, scope: !160)
!168 = !DILocalVariable(name: "flags", arg: 2, scope: !160, file: !3, line: 52, type: !85)
!169 = !DILocalVariable(name: "protocol", arg: 3, scope: !160, file: !3, line: 52, type: !94)
!170 = !DILocalVariable(name: "seq", arg: 4, scope: !160, file: !3, line: 52, type: !94)
!171 = !DILocalVariable(name: "pkt", arg: 5, scope: !160, file: !3, line: 52, type: !148)
!172 = !DILocalVariable(name: "pkt_len", arg: 6, scope: !160, file: !3, line: 52, type: !163)
!173 = !DILocalVariable(name: "sa", scope: !160, file: !3, line: 55, type: !174)
!174 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "sockaddr_nl", file: !66, line: 37, size: 96, elements: !175)
!175 = !{!176, !179, !180, !181}
!176 = !DIDerivedType(tag: DW_TAG_member, name: "nl_family", scope: !174, file: !66, line: 38, baseType: !177, size: 16)
!177 = !DIDerivedType(tag: DW_TAG_typedef, name: "__kernel_sa_family_t", file: !178, line: 10, baseType: !59)
!178 = !DIFile(filename: "/usr/include/linux/socket.h", directory: "", checksumkind: CSK_MD5, checksum: "58a7a04b3367680461e48f2eaee1699a")
!179 = !DIDerivedType(tag: DW_TAG_member, name: "nl_pad", scope: !174, file: !66, line: 39, baseType: !59, size: 16, offset: 16)
!180 = !DIDerivedType(tag: DW_TAG_member, name: "nl_pid", scope: !174, file: !66, line: 40, baseType: !69, size: 32, offset: 32)
!181 = !DIDerivedType(tag: DW_TAG_member, name: "nl_groups", scope: !174, file: !66, line: 41, baseType: !69, size: 32, offset: 64)
!182 = !DILocation(line: 55, column: 24, scope: !160)
!183 = !DILocalVariable(name: "m", scope: !160, file: !3, line: 56, type: !184)
!184 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "msghdr", file: !54, line: 259, size: 448, elements: !185)
!185 = !{!186, !187, !190, !197, !198, !199, !200}
!186 = !DIDerivedType(tag: DW_TAG_member, name: "msg_name", scope: !184, file: !54, line: 261, baseType: !76, size: 64)
!187 = !DIDerivedType(tag: DW_TAG_member, name: "msg_namelen", scope: !184, file: !54, line: 262, baseType: !188, size: 32, offset: 64)
!188 = !DIDerivedType(tag: DW_TAG_typedef, name: "socklen_t", file: !54, line: 33, baseType: !189)
!189 = !DIDerivedType(tag: DW_TAG_typedef, name: "__socklen_t", file: !88, line: 210, baseType: !7)
!190 = !DIDerivedType(tag: DW_TAG_member, name: "msg_iov", scope: !184, file: !54, line: 264, baseType: !191, size: 64, offset: 128)
!191 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !192, size: 64)
!192 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "iovec", file: !193, line: 26, size: 128, elements: !194)
!193 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/types/struct_iovec.h", directory: "", checksumkind: CSK_MD5, checksum: "906dd4c9f8205bfe8a00a7ac49f298dc")
!194 = !{!195, !196}
!195 = !DIDerivedType(tag: DW_TAG_member, name: "iov_base", scope: !192, file: !193, line: 28, baseType: !76, size: 64)
!196 = !DIDerivedType(tag: DW_TAG_member, name: "iov_len", scope: !192, file: !193, line: 29, baseType: !163, size: 64, offset: 64)
!197 = !DIDerivedType(tag: DW_TAG_member, name: "msg_iovlen", scope: !184, file: !54, line: 265, baseType: !163, size: 64, offset: 192)
!198 = !DIDerivedType(tag: DW_TAG_member, name: "msg_control", scope: !184, file: !54, line: 267, baseType: !76, size: 64, offset: 256)
!199 = !DIDerivedType(tag: DW_TAG_member, name: "msg_controllen", scope: !184, file: !54, line: 268, baseType: !163, size: 64, offset: 320)
!200 = !DIDerivedType(tag: DW_TAG_member, name: "msg_flags", scope: !184, file: !54, line: 273, baseType: !101, size: 32, offset: 384)
!201 = !DILocation(line: 56, column: 19, scope: !160)
!202 = !DILocation(line: 59, column: 87, scope: !160)
!203 = !DILocation(line: 59, column: 93, scope: !160)
!204 = !DILocation(line: 59, column: 5, scope: !160)
!205 = !DILocation(line: 61, column: 5, scope: !160)
!206 = !DILocation(line: 62, column: 5, scope: !160)
!207 = !DILocation(line: 63, column: 8, scope: !160)
!208 = !DILocation(line: 63, column: 18, scope: !160)
!209 = !DILocation(line: 65, column: 51, scope: !160)
!210 = !DILocalVariable(name: "pkt_full_len", scope: !160, file: !3, line: 65, type: !163)
!211 = !DILocation(line: 66, column: 25, scope: !160)
!212 = !DILocalVariable(name: "pkt_full", scope: !160, file: !3, line: 66, type: !148)
!213 = !DILocation(line: 67, column: 5, scope: !160)
!214 = !DILocation(line: 68, column: 21, scope: !160)
!215 = !DILocation(line: 68, column: 5, scope: !160)
!216 = !DILocation(line: 70, column: 36, scope: !160)
!217 = !DILocalVariable(name: "netlink_hdr", scope: !160, file: !3, line: 70, type: !64)
!218 = !DILocation(line: 71, column: 30, scope: !160)
!219 = !DILocation(line: 71, column: 18, scope: !160)
!220 = !DILocation(line: 71, column: 28, scope: !160)
!221 = !DILocation(line: 72, column: 18, scope: !160)
!222 = !DILocation(line: 72, column: 29, scope: !160)
!223 = !DILocation(line: 73, column: 18, scope: !160)
!224 = !DILocation(line: 73, column: 30, scope: !160)
!225 = !DILocation(line: 74, column: 18, scope: !160)
!226 = !DILocation(line: 74, column: 28, scope: !160)
!227 = !DILocation(line: 75, column: 30, scope: !160)
!228 = !DILocation(line: 75, column: 18, scope: !160)
!229 = !DILocation(line: 75, column: 28, scope: !160)
!230 = !DILocation(line: 77, column: 20, scope: !231)
!231 = distinct !DILexicalBlock(scope: !160, file: !3, line: 77, column: 9)
!232 = !DILocalVariable(name: "sock_fd", scope: !160, file: !3, line: 54, type: !101)
!233 = !DILocation(line: 77, column: 60, scope: !231)
!234 = !DILocation(line: 77, column: 9, scope: !160)
!235 = !DILocation(line: 78, column: 9, scope: !236)
!236 = distinct !DILexicalBlock(scope: !231, file: !3, line: 77, column: 65)
!237 = !DILocation(line: 79, column: 9, scope: !236)
!238 = !DILocation(line: 82, column: 23, scope: !239)
!239 = distinct !DILexicalBlock(scope: !160, file: !3, line: 82, column: 9)
!240 = !DILocation(line: 82, column: 9, scope: !239)
!241 = !DILocation(line: 82, column: 58, scope: !239)
!242 = !DILocation(line: 82, column: 9, scope: !160)
!243 = !DILocation(line: 83, column: 9, scope: !244)
!244 = distinct !DILexicalBlock(scope: !239, file: !3, line: 82, column: 63)
!245 = !DILocation(line: 84, column: 9, scope: !244)
!246 = !DILocation(line: 87, column: 17, scope: !160)
!247 = !DILocalVariable(name: "r", scope: !160, file: !3, line: 87, type: !248)
!248 = !DIDerivedType(tag: DW_TAG_typedef, name: "ssize_t", file: !249, line: 77, baseType: !250)
!249 = !DIFile(filename: "/usr/include/stdio.h", directory: "", checksumkind: CSK_MD5, checksum: "f31eefcc3f15835fc5a4023a625cf609")
!250 = !DIDerivedType(tag: DW_TAG_typedef, name: "__ssize_t", file: !88, line: 194, baseType: !251)
!251 = !DIBasicType(name: "long", size: 64, encoding: DW_ATE_signed)
!252 = !DILocation(line: 92, column: 11, scope: !253)
!253 = distinct !DILexicalBlock(scope: !160, file: !3, line: 92, column: 9)
!254 = !DILocation(line: 92, column: 9, scope: !160)
!255 = !DILocation(line: 93, column: 9, scope: !256)
!256 = distinct !DILexicalBlock(scope: !253, file: !3, line: 92, column: 16)
!257 = !DILocation(line: 94, column: 9, scope: !256)
!258 = !DILocation(line: 97, column: 5, scope: !160)
!259 = !DILocation(line: 100, column: 7, scope: !160)
!260 = !DILocation(line: 100, column: 18, scope: !160)
!261 = !DILocation(line: 101, column: 17, scope: !160)
!262 = !DILocation(line: 101, column: 7, scope: !160)
!263 = !DILocation(line: 101, column: 15, scope: !160)
!264 = !DILocation(line: 102, column: 27, scope: !160)
!265 = !DILocation(line: 102, column: 16, scope: !160)
!266 = !DILocation(line: 102, column: 25, scope: !160)
!267 = !DILocation(line: 103, column: 16, scope: !160)
!268 = !DILocation(line: 103, column: 24, scope: !160)
!269 = !DILocation(line: 105, column: 18, scope: !270)
!270 = distinct !DILexicalBlock(scope: !160, file: !3, line: 105, column: 9)
!271 = !DILocalVariable(name: "nread", scope: !160, file: !3, line: 57, type: !163)
!272 = !DILocation(line: 105, column: 9, scope: !160)
!273 = !DILabel(scope: !160, name: "error", file: !3, line: 114)
!274 = !DILocation(line: 114, column: 1, scope: !160)
!275 = !DILocation(line: 115, column: 5, scope: !160)
!276 = !DILocation(line: 116, column: 5, scope: !160)
!277 = !DILocation(line: 109, column: 12, scope: !160)
!278 = !DILocation(line: 109, column: 21, scope: !160)
!279 = !DILocation(line: 109, column: 5, scope: !160)
!280 = !DILocation(line: 111, column: 5, scope: !160)
!281 = !DILocation(line: 112, column: 5, scope: !160)
!282 = !DILocation(line: 117, column: 1, scope: !160)
!283 = distinct !DISubprogram(name: "send_netlink_packet", scope: !3, file: !3, line: 127, type: !284, scopeLine: 128, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!284 = !DISubroutineType(types: !285)
!285 = !{!101, !148, !94}
!286 = !DILocalVariable(name: "blob", arg: 1, scope: !283, file: !3, line: 127, type: !148)
!287 = !DILocation(line: 0, scope: !283)
!288 = !DILocalVariable(name: "blob_size", arg: 2, scope: !283, file: !3, line: 127, type: !94)
!289 = !DILocalVariable(name: "index", scope: !283, file: !3, line: 129, type: !101)
!290 = !DILocalVariable(name: "packet_size", scope: !283, file: !3, line: 130, type: !94)
!291 = !DILocation(line: 130, column: 14, scope: !283)
!292 = !DILocalVariable(name: "msg_type", scope: !283, file: !3, line: 131, type: !94)
!293 = !DILocation(line: 131, column: 14, scope: !283)
!294 = !DILocalVariable(name: "msg_flags", scope: !283, file: !3, line: 132, type: !94)
!295 = !DILocation(line: 132, column: 14, scope: !283)
!296 = !DILocalVariable(name: "protocol", scope: !283, file: !3, line: 133, type: !94)
!297 = !DILocation(line: 133, column: 14, scope: !283)
!298 = !DILocation(line: 135, column: 15, scope: !299)
!299 = distinct !DILexicalBlock(scope: !283, file: !3, line: 135, column: 10)
!300 = !DILocation(line: 135, column: 10, scope: !283)
!301 = !DILocation(line: 136, column: 9, scope: !302)
!302 = distinct !DILexicalBlock(scope: !299, file: !3, line: 135, column: 25)
!303 = !DILocation(line: 139, column: 20, scope: !304)
!304 = distinct !DILexicalBlock(scope: !283, file: !3, line: 139, column: 10)
!305 = !DILocation(line: 139, column: 10, scope: !283)
!306 = !DILocation(line: 140, column: 9, scope: !307)
!307 = distinct !DILexicalBlock(scope: !304, file: !3, line: 139, column: 27)
!308 = !DILocation(line: 143, column: 5, scope: !283)
!309 = !DILocation(line: 144, column: 5, scope: !283)
!310 = !DILocation(line: 144, column: 29, scope: !283)
!311 = !DILocation(line: 145, column: 5, scope: !283)
!312 = !DILocation(line: 145, column: 28, scope: !283)
!313 = !DILocation(line: 146, column: 5, scope: !283)
!314 = !DILocation(line: 146, column: 31, scope: !283)
!315 = !DILocation(line: 150, column: 20, scope: !316)
!316 = distinct !DILexicalBlock(scope: !283, file: !3, line: 150, column: 10)
!317 = !DILocation(line: 150, column: 30, scope: !316)
!318 = !DILocation(line: 150, column: 28, scope: !316)
!319 = !DILocation(line: 150, column: 10, scope: !283)
!320 = !DILocation(line: 151, column: 9, scope: !321)
!321 = distinct !DILexicalBlock(scope: !316, file: !3, line: 150, column: 44)
!322 = !DILocation(line: 154, column: 24, scope: !323)
!323 = distinct !DILexicalBlock(scope: !283, file: !3, line: 154, column: 10)
!324 = !DILocation(line: 154, column: 34, scope: !323)
!325 = !DILocation(line: 154, column: 45, scope: !323)
!326 = !DILocation(line: 154, column: 55, scope: !323)
!327 = !DILocation(line: 154, column: 72, scope: !323)
!328 = !DILocation(line: 154, column: 81, scope: !323)
!329 = !DILocation(line: 154, column: 10, scope: !323)
!330 = !DILocation(line: 154, column: 94, scope: !323)
!331 = !DILocation(line: 154, column: 10, scope: !283)
!332 = !DILocation(line: 155, column: 9, scope: !333)
!333 = distinct !DILexicalBlock(scope: !323, file: !3, line: 154, column: 100)
!334 = !DILocation(line: 158, column: 11, scope: !283)
!335 = !DILocation(line: 160, column: 5, scope: !283)
!336 = !DILocation(line: 162, column: 5, scope: !283)
!337 = !DILocation(line: 163, column: 1, scope: !283)
!338 = distinct !DISubprogram(name: "harness", scope: !3, file: !3, line: 175, type: !284, scopeLine: 176, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!339 = !DILocalVariable(name: "blob", arg: 1, scope: !338, file: !3, line: 175, type: !148)
!340 = !DILocation(line: 0, scope: !338)
!341 = !DILocalVariable(name: "blob_size", arg: 2, scope: !338, file: !3, line: 175, type: !94)
!342 = !DILocalVariable(name: "index", scope: !338, file: !3, line: 177, type: !101)
!343 = !DILocalVariable(name: "command", scope: !338, file: !3, line: 178, type: !94)
!344 = !DILocation(line: 178, column: 14, scope: !338)
!345 = !DILocalVariable(name: "command_count", scope: !338, file: !3, line: 178, type: !94)
!346 = !DILocation(line: 178, column: 23, scope: !338)
!347 = !DILocalVariable(name: "flags", scope: !338, file: !3, line: 179, type: !94)
!348 = !DILocation(line: 179, column: 14, scope: !338)
!349 = !DILocalVariable(name: "packet_size", scope: !338, file: !3, line: 179, type: !94)
!350 = !DILocation(line: 179, column: 21, scope: !338)
!351 = !DILocalVariable(name: "domain", scope: !338, file: !3, line: 180, type: !94)
!352 = !DILocation(line: 180, column: 14, scope: !338)
!353 = !DILocalVariable(name: "type", scope: !338, file: !3, line: 180, type: !94)
!354 = !DILocation(line: 180, column: 22, scope: !338)
!355 = !DILocalVariable(name: "protocol", scope: !338, file: !3, line: 180, type: !94)
!356 = !DILocation(line: 180, column: 28, scope: !338)
!357 = !DILocalVariable(name: "port", scope: !338, file: !3, line: 181, type: !85)
!358 = !DILocation(line: 181, column: 14, scope: !338)
!359 = !DILocalVariable(name: "level", scope: !338, file: !3, line: 184, type: !94)
!360 = !DILocation(line: 184, column: 14, scope: !338)
!361 = !DILocalVariable(name: "optname", scope: !338, file: !3, line: 184, type: !94)
!362 = !DILocation(line: 184, column: 21, scope: !338)
!363 = !DILocalVariable(name: "optval", scope: !338, file: !3, line: 184, type: !94)
!364 = !DILocation(line: 184, column: 30, scope: !338)
!365 = !DILocation(line: 186, column: 15, scope: !366)
!366 = distinct !DILexicalBlock(scope: !338, file: !3, line: 186, column: 10)
!367 = !DILocation(line: 186, column: 10, scope: !338)
!368 = !DILocation(line: 187, column: 9, scope: !369)
!369 = distinct !DILexicalBlock(scope: !366, file: !3, line: 186, column: 25)
!370 = !DILocation(line: 191, column: 10, scope: !371)
!371 = distinct !DILexicalBlock(scope: !338, file: !3, line: 191, column: 10)
!372 = !DILocation(line: 191, column: 63, scope: !371)
!373 = !DILocation(line: 191, column: 10, scope: !338)
!374 = !DILocation(line: 192, column: 9, scope: !375)
!375 = distinct !DILexicalBlock(scope: !371, file: !3, line: 191, column: 69)
!376 = !DILocation(line: 197, column: 20, scope: !377)
!377 = distinct !DILexicalBlock(scope: !338, file: !3, line: 197, column: 10)
!378 = !DILocation(line: 197, column: 10, scope: !338)
!379 = !DILocation(line: 198, column: 9, scope: !380)
!380 = distinct !DILexicalBlock(scope: !377, file: !3, line: 197, column: 26)
!381 = !DILocation(line: 201, column: 5, scope: !338)
!382 = !DILocation(line: 204, column: 46, scope: !338)
!383 = !DILocation(line: 204, column: 5, scope: !338)
!384 = !DILocalVariable(name: "i", scope: !385, file: !3, line: 206, type: !101)
!385 = distinct !DILexicalBlock(scope: !338, file: !3, line: 206, column: 5)
!386 = !DILocation(line: 0, scope: !385)
!387 = !DILocation(line: 206, column: 11, scope: !385)
!388 = !DILocation(line: 206, column: 24, scope: !389)
!389 = distinct !DILexicalBlock(scope: !385, file: !3, line: 206, column: 5)
!390 = !DILocation(line: 206, column: 5, scope: !385)
!391 = !DILocation(line: 207, column: 24, scope: !392)
!392 = distinct !DILexicalBlock(scope: !393, file: !3, line: 207, column: 14)
!393 = distinct !DILexicalBlock(scope: !389, file: !3, line: 206, column: 46)
!394 = !DILocation(line: 207, column: 32, scope: !392)
!395 = !DILocation(line: 207, column: 14, scope: !393)
!396 = !DILocation(line: 208, column: 13, scope: !397)
!397 = distinct !DILexicalBlock(scope: !392, file: !3, line: 207, column: 38)
!398 = !DILocation(line: 211, column: 9, scope: !393)
!399 = !DILocation(line: 211, column: 31, scope: !393)
!400 = !DILocation(line: 212, column: 15, scope: !393)
!401 = !DILocation(line: 214, column: 18, scope: !393)
!402 = !DILocation(line: 214, column: 9, scope: !393)
!403 = !DILocation(line: 216, column: 28, scope: !404)
!404 = distinct !DILexicalBlock(scope: !405, file: !3, line: 216, column: 18)
!405 = distinct !DILexicalBlock(scope: !393, file: !3, line: 214, column: 28)
!406 = !DILocation(line: 216, column: 36, scope: !404)
!407 = !DILocation(line: 216, column: 18, scope: !405)
!408 = !DILocation(line: 217, column: 23, scope: !409)
!409 = distinct !DILexicalBlock(scope: !404, file: !3, line: 216, column: 42)
!410 = !DILocation(line: 217, column: 17, scope: !409)
!411 = !DILocation(line: 218, column: 17, scope: !409)
!412 = !DILocation(line: 221, column: 13, scope: !405)
!413 = !DILocation(line: 221, column: 39, scope: !405)
!414 = !DILocation(line: 222, column: 13, scope: !405)
!415 = !DILocation(line: 222, column: 41, scope: !405)
!416 = !DILocation(line: 223, column: 19, scope: !405)
!417 = !DILocation(line: 225, column: 28, scope: !418)
!418 = distinct !DILexicalBlock(scope: !405, file: !3, line: 225, column: 18)
!419 = !DILocation(line: 225, column: 38, scope: !418)
!420 = !DILocation(line: 225, column: 36, scope: !418)
!421 = !DILocation(line: 225, column: 18, scope: !405)
!422 = !DILocation(line: 226, column: 23, scope: !423)
!423 = distinct !DILexicalBlock(scope: !418, file: !3, line: 225, column: 52)
!424 = !DILocation(line: 226, column: 17, scope: !423)
!425 = !DILocation(line: 227, column: 17, scope: !423)
!426 = !DILocation(line: 230, column: 34, scope: !427)
!427 = distinct !DILexicalBlock(scope: !405, file: !3, line: 230, column: 18)
!428 = !DILocation(line: 230, column: 43, scope: !427)
!429 = !DILocation(line: 230, column: 18, scope: !427)
!430 = !DILocation(line: 230, column: 64, scope: !427)
!431 = !DILocation(line: 230, column: 18, scope: !405)
!432 = !DILocation(line: 231, column: 23, scope: !433)
!433 = distinct !DILexicalBlock(scope: !427, file: !3, line: 230, column: 69)
!434 = !DILocation(line: 231, column: 17, scope: !433)
!435 = !DILocation(line: 232, column: 17, scope: !433)
!436 = !DILocation(line: 235, column: 19, scope: !405)
!437 = !DILocation(line: 236, column: 13, scope: !405)
!438 = !DILocation(line: 238, column: 45, scope: !405)
!439 = !DILocation(line: 238, column: 64, scope: !405)
!440 = !DILocation(line: 238, column: 19, scope: !405)
!441 = !DILocalVariable(name: "res", scope: !338, file: !3, line: 182, type: !101)
!442 = !DILocation(line: 240, column: 22, scope: !443)
!443 = distinct !DILexicalBlock(scope: !405, file: !3, line: 240, column: 18)
!444 = !DILocation(line: 240, column: 18, scope: !405)
!445 = !DILocation(line: 241, column: 17, scope: !446)
!446 = distinct !DILexicalBlock(scope: !443, file: !3, line: 240, column: 28)
!447 = !DILocation(line: 242, column: 17, scope: !446)
!448 = !DILocation(line: 245, column: 19, scope: !405)
!449 = !DILocation(line: 247, column: 13, scope: !405)
!450 = !DILocation(line: 249, column: 13, scope: !405)
!451 = !DILocation(line: 250, column: 13, scope: !405)
!452 = !DILocation(line: 0, scope: !405)
!453 = !DILocation(line: 206, column: 42, scope: !389)
!454 = !DILocation(line: 206, column: 5, scope: !389)
!455 = distinct !{!455, !390, !456, !457}
!456 = !DILocation(line: 253, column: 5, scope: !385)
!457 = !{!"llvm.loop.mustprogress"}
!458 = !DILocation(line: 255, column: 5, scope: !338)
!459 = !DILocation(line: 256, column: 11, scope: !338)
!460 = !DILocation(line: 256, column: 5, scope: !338)
!461 = !DILocation(line: 257, column: 5, scope: !338)
!462 = !DILocation(line: 258, column: 1, scope: !338)
!463 = distinct !DISubprogram(name: "main", scope: !3, file: !3, line: 260, type: !464, scopeLine: 261, flags: DIFlagPrototyped, spFlags: DISPFlagDefinition, unit: !2, retainedNodes: !113)
!464 = !DISubroutineType(types: !465)
!465 = !{!101, !101, !466}
!466 = !DIDerivedType(tag: DW_TAG_pointer_type, baseType: !50, size: 64)
!467 = !DILocalVariable(name: "argc", arg: 1, scope: !463, file: !3, line: 260, type: !101)
!468 = !DILocation(line: 0, scope: !463)
!469 = !DILocalVariable(name: "argv", arg: 2, scope: !463, file: !3, line: 260, type: !466)
!470 = !DILocalVariable(name: "blob", scope: !463, file: !3, line: 262, type: !50)
!471 = !DILocalVariable(name: "st", scope: !463, file: !3, line: 263, type: !472)
!472 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "stat", file: !473, line: 26, size: 1152, elements: !474)
!473 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/struct_stat.h", directory: "", checksumkind: CSK_MD5, checksum: "3ba283bc334370fe631cbc82f5229ed7")
!474 = !{!475, !477, !479, !481, !483, !485, !487, !488, !489, !491, !493, !495, !503, !504, !505}
!475 = !DIDerivedType(tag: DW_TAG_member, name: "st_dev", scope: !472, file: !473, line: 31, baseType: !476, size: 64)
!476 = !DIDerivedType(tag: DW_TAG_typedef, name: "__dev_t", file: !88, line: 145, baseType: !165)
!477 = !DIDerivedType(tag: DW_TAG_member, name: "st_ino", scope: !472, file: !473, line: 36, baseType: !478, size: 64, offset: 64)
!478 = !DIDerivedType(tag: DW_TAG_typedef, name: "__ino_t", file: !88, line: 148, baseType: !165)
!479 = !DIDerivedType(tag: DW_TAG_member, name: "st_nlink", scope: !472, file: !473, line: 44, baseType: !480, size: 64, offset: 128)
!480 = !DIDerivedType(tag: DW_TAG_typedef, name: "__nlink_t", file: !88, line: 151, baseType: !165)
!481 = !DIDerivedType(tag: DW_TAG_member, name: "st_mode", scope: !472, file: !473, line: 45, baseType: !482, size: 32, offset: 192)
!482 = !DIDerivedType(tag: DW_TAG_typedef, name: "__mode_t", file: !88, line: 150, baseType: !7)
!483 = !DIDerivedType(tag: DW_TAG_member, name: "st_uid", scope: !472, file: !473, line: 47, baseType: !484, size: 32, offset: 224)
!484 = !DIDerivedType(tag: DW_TAG_typedef, name: "__uid_t", file: !88, line: 146, baseType: !7)
!485 = !DIDerivedType(tag: DW_TAG_member, name: "st_gid", scope: !472, file: !473, line: 48, baseType: !486, size: 32, offset: 256)
!486 = !DIDerivedType(tag: DW_TAG_typedef, name: "__gid_t", file: !88, line: 147, baseType: !7)
!487 = !DIDerivedType(tag: DW_TAG_member, name: "__pad0", scope: !472, file: !473, line: 50, baseType: !101, size: 32, offset: 288)
!488 = !DIDerivedType(tag: DW_TAG_member, name: "st_rdev", scope: !472, file: !473, line: 52, baseType: !476, size: 64, offset: 320)
!489 = !DIDerivedType(tag: DW_TAG_member, name: "st_size", scope: !472, file: !473, line: 57, baseType: !490, size: 64, offset: 384)
!490 = !DIDerivedType(tag: DW_TAG_typedef, name: "__off_t", file: !88, line: 152, baseType: !251)
!491 = !DIDerivedType(tag: DW_TAG_member, name: "st_blksize", scope: !472, file: !473, line: 61, baseType: !492, size: 64, offset: 448)
!492 = !DIDerivedType(tag: DW_TAG_typedef, name: "__blksize_t", file: !88, line: 175, baseType: !251)
!493 = !DIDerivedType(tag: DW_TAG_member, name: "st_blocks", scope: !472, file: !473, line: 63, baseType: !494, size: 64, offset: 512)
!494 = !DIDerivedType(tag: DW_TAG_typedef, name: "__blkcnt_t", file: !88, line: 180, baseType: !251)
!495 = !DIDerivedType(tag: DW_TAG_member, name: "st_atim", scope: !472, file: !473, line: 74, baseType: !496, size: 128, offset: 576)
!496 = distinct !DICompositeType(tag: DW_TAG_structure_type, name: "timespec", file: !497, line: 11, size: 128, elements: !498)
!497 = !DIFile(filename: "/usr/include/x86_64-linux-gnu/bits/types/struct_timespec.h", directory: "", checksumkind: CSK_MD5, checksum: "55dc154df3f21a5aa944dcafba9b43f6")
!498 = !{!499, !501}
!499 = !DIDerivedType(tag: DW_TAG_member, name: "tv_sec", scope: !496, file: !497, line: 16, baseType: !500, size: 64)
!500 = !DIDerivedType(tag: DW_TAG_typedef, name: "__time_t", file: !88, line: 160, baseType: !251)
!501 = !DIDerivedType(tag: DW_TAG_member, name: "tv_nsec", scope: !496, file: !497, line: 21, baseType: !502, size: 64, offset: 64)
!502 = !DIDerivedType(tag: DW_TAG_typedef, name: "__syscall_slong_t", file: !88, line: 197, baseType: !251)
!503 = !DIDerivedType(tag: DW_TAG_member, name: "st_mtim", scope: !472, file: !473, line: 75, baseType: !496, size: 128, offset: 704)
!504 = !DIDerivedType(tag: DW_TAG_member, name: "st_ctim", scope: !472, file: !473, line: 76, baseType: !496, size: 128, offset: 832)
!505 = !DIDerivedType(tag: DW_TAG_member, name: "__glibc_reserved", scope: !472, file: !473, line: 89, baseType: !506, size: 192, offset: 960)
!506 = !DICompositeType(tag: DW_TAG_array_type, baseType: !502, size: 192, elements: !507)
!507 = !{!508}
!508 = !DISubrange(count: 3)
!509 = !DILocation(line: 263, column: 17, scope: !463)
!510 = !DILocation(line: 266, column: 14, scope: !511)
!511 = distinct !DILexicalBlock(scope: !463, file: !3, line: 266, column: 9)
!512 = !DILocation(line: 266, column: 9, scope: !463)
!513 = !DILocation(line: 267, column: 9, scope: !514)
!514 = distinct !DILexicalBlock(scope: !511, file: !3, line: 266, column: 19)
!515 = !DILocation(line: 268, column: 9, scope: !514)
!516 = !DILocation(line: 271, column: 15, scope: !517)
!517 = distinct !DILexicalBlock(scope: !463, file: !3, line: 271, column: 10)
!518 = !DILocation(line: 271, column: 10, scope: !517)
!519 = !DILocation(line: 271, column: 29, scope: !517)
!520 = !DILocation(line: 271, column: 10, scope: !463)
!521 = !DILocation(line: 272, column: 9, scope: !522)
!522 = distinct !DILexicalBlock(scope: !517, file: !3, line: 271, column: 35)
!523 = !DILocation(line: 273, column: 9, scope: !522)
!524 = !DILocation(line: 276, column: 15, scope: !463)
!525 = !DILocation(line: 276, column: 10, scope: !463)
!526 = !DILocalVariable(name: "fd", scope: !463, file: !3, line: 264, type: !101)
!527 = !DILocation(line: 278, column: 13, scope: !528)
!528 = distinct !DILexicalBlock(scope: !463, file: !3, line: 278, column: 10)
!529 = !DILocation(line: 278, column: 10, scope: !463)
!530 = !DILocation(line: 279, column: 9, scope: !531)
!531 = distinct !DILexicalBlock(scope: !528, file: !3, line: 278, column: 19)
!532 = !DILocation(line: 280, column: 9, scope: !531)
!533 = !DILocation(line: 283, column: 22, scope: !463)
!534 = !DILocation(line: 283, column: 12, scope: !463)
!535 = !DILocation(line: 285, column: 15, scope: !536)
!536 = distinct !DILexicalBlock(scope: !463, file: !3, line: 285, column: 10)
!537 = !DILocation(line: 285, column: 10, scope: !463)
!538 = !DILocation(line: 286, column: 9, scope: !539)
!539 = distinct !DILexicalBlock(scope: !536, file: !3, line: 285, column: 25)
!540 = !DILocation(line: 289, column: 5, scope: !463)
!541 = !DILocation(line: 291, column: 5, scope: !463)
!542 = !DILocation(line: 293, column: 22, scope: !463)
!543 = !DILocation(line: 293, column: 19, scope: !463)
!544 = !DILocation(line: 293, column: 5, scope: !463)
!545 = !DILocation(line: 295, column: 5, scope: !463)
!546 = !DILocation(line: 296, column: 1, scope: !463)
