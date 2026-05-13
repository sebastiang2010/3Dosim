function [volumen] = f_volumen(organo,vCT,Phantom)

%          if organo==30;txt='Tejido Blando';end
%          if organo==50;txt='Pulmon';end
%          if organo==80;txt='Hueso';end
%          if organo==90;txt='Higado sano';c='b';end    
%          if organo>=100;txt='Tumor';c='r';end
%          if organo==99;txt='Pretumor';c='g';end
         
        
         ind=Phantom==organo;
         B=Phantom(ind);
         n=numel(B); %numero de pixel
         
         volumen=n*prod(vCT); %cm


end

