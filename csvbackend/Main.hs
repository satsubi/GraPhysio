{-# LANGUAGE OverloadedStrings #-}
module Main where

import Util
import ProcessTable

import Network.Socket hiding (send, sendTo, recv, recvFrom)
import Network.Socket.ByteString.Lazy
import Prelude hiding (getContents)

import           Control.Concurrent (forkIO)
import           Control.Monad (forever)
import qualified Data.ByteString.Lazy.Char8 as C
--import           System.Directory (doesFileExist)
import           System.IO.Error (catchIOError)
import           Text.Read

-- | Convert string protocol to Commands
parseCommands :: String -> Command
parseCommands cmdStr = parsedCmd
  where
    parse     = (readMaybe cmdStr) :: Maybe Command
    parsedCmd = case parse of
                  Just cmd -> cmd
                  Nothing  -> ErrSyntax

-- | Generate Status message
genStatus :: String -> C.ByteString
genStatus s = C.snoc (C.pack s) '\n'

-- | Generate a reply for the given request
genReply :: Command -> (Socket -> IO (), IO C.ByteString, Socket -> IO ())
genReply cmd = (preaction, msg, postaction)
  where
--  fileexists <- doesFileExist (fileName c)
    preaction = case cmd of
               c@(ReadVector{}) -> \sock -> sendAll sock (genStatus "Ok")
               _                -> \_    -> return ()

    postaction = case cmd of
               CloseConnection -> \sock -> close sock
               _               -> \_    -> return ()

    msg    = case cmd of
               c@(ReadVector{}) -> serialize `fmap` processCsv c
               CloseConnection  -> return $ genStatus "Closing Connection"
               ErrSyntax        -> return $ genStatus "Syntax Error"

main :: IO ()
main = forever mainLoop
 
mainLoop :: IO ()
mainLoop = do
  sock <- socket AF_INET Stream 0
  setSocketOption sock ReuseAddr 1
  setSocketOption sock ReusePort 1
  bind sock (SockAddrInet 4242 iNADDR_ANY)
  listen sock 1
  (sock, addr) <- accept sock
  forkIO $ whileM_ (isConnected sock) $ catchIOError (serve sock) (\_ -> close sock)
  return ()
 
-- | Handle requests
serve :: Socket -> IO ()
serve sock = do
  cmd <- recv sock 1024
  let ret = parseCommands (C.unpack cmd)
  let (preaction, msg, postaction) = genReply ret
  lemsg <- msg
  do (preaction sock)
  sendAll sock lemsg
  do (postaction sock)
