classdef XmlSpecifiedRuleCheck < handle
    %XMLSPECIFIEDRULECHECK This class is doing the parsing of placement rules defined
    %in xml format and then checks individual cells.    
    
    properties(Access=private)
        ruleSetFile;
        ruleSets;
        
        morphologyRuleInstances;
        layerInfo;
        
        results;
        
        yBinsSize; %TODO: offer set function
        layerBins;
        transferFcn;
        ruleCheckFcn;
    end
    properties(Access=public)
        strictness;
    end
    
    methods
        function obj = XmlSpecifiedRuleCheck(file,lInfo)
            obj.ruleSetFile = file;
            obj.layerInfo = lInfo;
            obj.yBinsSize = 10; %micron            
            obj.transferFcn.default = @(x)x;
            obj.transferFcn.upper_hard_limit = @(x)obj.upper_hard_limit(x);
            obj.ruleCheckFcn.region_target = @(instance,rule,bins)obj.checkRegionTarget(instance,rule,bins);
            obj.ruleCheckFcn.below = @(instance,rule,bins)obj.checkYBelow(instance,rule,bins);
            obj.makeLayerBins();
            obj.strictness = 50;
            obj.morphologyRuleInstances = [];
            %then do parsing here   
            if(exist('parseXML','file'))
                xml = parseXML(file);
            else
                xml = xml2struct(file);
            end
            obj.addRulesFromXml(xml.Children(cellfun(@(x)x(1)~='#',{xml.Children.Name})));
        end
        function [] = addMorphologyInstance(obj,file)
            %read new rule instances
            if(~exist(file,'file'))
                warning('PlacementHints:ReadRuleInstance:AnnotationsNotFound',...
                    'No annotation xml file found at %s. Adding morphology without constraints',file);
                [~,morphName] = fileparts(file);   
                %morphName = strrep(morphName,'-','_');
                obj.morphologyRuleInstances(end+1).morphName = morphName;
                obj.morphologyRuleInstances(end).rules = [];
                return
            end
            if(exist('parseXML','file'))
                xml = parseXML(file);
            else
                xml = xml2struct(file);
            end           
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameFieldLookup = @(x,str,fn)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).(fn)});
            if(isempty(xml.Attributes))
                warning('PlacementHints:ReadRuleInstance:MorphologyNotSpecified','Morphology name not specified in xml. Guessing from filename: %s',file);
                [~,morphName] = fileparts(file);                
            else
                morphName = nameFieldLookup(xml.Attributes,'morphology','Value');
            end
            %morphName = strrep(morphName,'-','_');
            obj.morphologyRuleInstances(end+1).morphName = morphName;
            annotations = xml.Children;
            annotations = annotations(cellfun(@(x)strcmp(x,'placement'),{annotations.Name}));
            for i = 1:length(annotations)
                instance = annotations(i).Attributes;
                
                ruleName = nameFieldLookup(instance,'rule','Value');
                obj.morphologyRuleInstances(end).rules(i).Rule = ruleName;                
                
                otherAttributes = setdiff({instance.Name},'rule');
                for j = 1:length(otherAttributes)
                    obj.morphologyRuleInstances(end).rules(i).(otherAttributes{j})=nameFieldLookup(instance,otherAttributes{j},'Value');
                end                
            end            
        end
        function scores = getResult(obj,morphName,inLayer,asMType)            
            scores = obj.checkMorphology(morphName,inLayer,asMType);            
            obj.results(end+1).morphology = morphName;
            obj.results(end).mtype = asMType;
            obj.results(end).scores = scores;
            obj.results(end).layer = inLayer;
        end
        function [] = plotOverview(obj,varargin)
            filter = ones(1,length(obj.results));
            titleStr = '';
            for i = 1:2:length(varargin)
                if(ischar(varargin{i+1}))
                    filter = filter.*cellfun(@(x)strcmp(x,varargin{i+1}),{obj.results.(varargin{i})});
                    titleStr = cat(2,titleStr,sprintf('%s is %s; ',varargin{i:i+1}));
                else
                    filter = filter.*(obj.results.(varargin{i})==varargin{i+1});
                    titleStr = cat(2,titleStr,sprintf('%s is %d; ',varargin{i:i+1}));
                end                 
            end
            valids = obj.results(find(filter));
            allYBins = catCell(2,obj.layerBins([valids.layer]));
            allScores = catCell(2,{valids.scores});
            figure('Position',[200 300 300 800]);
            boxplot(allScores,allYBins,'plotstyle','compact','orientation','horizontal');
            xlabel('score');ylabel('\mum');set(gca,'XLim',[0 max(get(gca,'XLim'))]);
            axes('Position',get(gca,'Position'),'Color','none','YTick',[],'XAxisLocation','top','XColor',[0.7 0 0]);
            line(cellfun(@(y)sum(allScores(allYBins==y)),num2cell(unique(allYBins))),unique(allYBins),'Color',[1 0 0]);            
            xlabel('total score'); set(gca,'XLim',[0 max(get(gca,'XLim'))],'YLim',[min(allYBins) max(allYBins)]);
            title(titleStr,'Interpreter','none');
        end
        function [] = writeChampions(obj,toFile)
            fid = fopen(toFile,'w');
            layerMType = cellfun(@(x,y)sprintf('Layer %d: %s',x,y),{obj.results.layer},{obj.results.mtype},'UniformOutput',false);
            umtype = unique(layerMType);
            for i = 1:length(umtype)
                fprintf(fid,'For mtype = %s\n',umtype{i});
                indices = find(cellfun(@(x)strcmp(x,umtype{i}),layerMType));                
                if(isempty(indices))
                    continue
                end
                bins = obj.layerBins{obj.results(indices(1)).layer};
                for j = 1:length(bins)
                    [scores sorted] = sort(cellfun(@(x)x(j),{obj.results(indices).scores}));
                    fprintf(fid,'\t%4.2f: %s -- %d\n',bins(j),obj.results(indices(sorted(end))).morphology,scores(end));
                    for k = max(length(scores)+[-1 -2],1)                        
                        fprintf(fid,'\t\t%s -- %d\n',obj.results(indices(sorted(k))).morphology,scores(k));
                    end
                end                
            end
            fclose(fid);
        end
        
    end
    methods(Access=private)        
        function scores = checkMorphology(obj,morphName,inLayer,asMType)
            finder = find(cellfun(@(x)strcmp(x,morphName),{obj.morphologyRuleInstances.morphName}),1);
            if(isempty(finder))
                error('PlacementHints:getResults:MorphologyNotAnnotated','Morphology %s has no rule instance file specified!',morphName);
            else
                relevantInstances = obj.morphologyRuleInstances(finder).rules;
                if(~isfield(obj.ruleSets,asMType))
                    %error('PlacementHints:getResults:MTypeNotKnown','Cannot find rules for MType %s!',asMType);
                    relevantRuleSet = struct();
                else
                    relevantRuleSet = obj.ruleSets.(asMType); 
                end                
                
                scores = ones(0,length(obj.layerBins{inLayer}));
                for i = 1:length(relevantInstances)
                    if(~isfield(relevantRuleSet,relevantInstances(i).Rule))
                        if(isfield(obj.ruleSets.global,relevantInstances(i).Rule))
                            relevantRule = obj.ruleSets.global.(relevantInstances(i).Rule);
                        else
                            error('PlacementHints:getResults:UnknownRule','Rule instance refers to rule %s in %s, which is not defined! Neither defined as global',...
                            relevantInstances(i).Rule,relevantRuleSet.mtype);
                        end
                    else
                        relevantRule = relevantRuleSet.(relevantInstances(i).Rule);
                    end                    
                    if(isfield(relevantInstances(i),'transferFcn'))
                        tferFunc = obj.transferFcn.(strrep(relevantInstances(i).transferFcn,'-','_'));
                    else
                        tferFunc = obj.transferFcn.default;
                    end
                    scores(i,:) = tferFunc(obj.ruleCheckFcn.(relevantRule.type)(relevantInstances(i),relevantRule,obj.layerBins{inLayer}));
                end
                scores = obj.mergeScores(scores);
            end
        end
        
        function scores = mergeScores(obj,scores)  
            if(isempty(scores))
                scores = ones(1,size(scores,2));
                return;
            end
            fcn = @(x,p)((sum(x.^p)/length(x))^(1/p))*all(x>=0);
            shapeParameter = norminv(obj.strictness/101,1,2.25);            
            baseWeight = size(scores,1).*(log10(obj.strictness).^7);
            scores = round(baseWeight.*cellfun(@(x)fcn(x,shapeParameter),num2cell(scores,1)));%+ones(1,size(scores,2)));
        end
        
        %Function subject to change if we ever inplement more than just y
        %intervals. For now lazily implemented
        function interval = getLayerInterval(obj,rule,fields)
            fractionLookup = @(iv,f)iv(1)+f*diff(iv);
            getIv = @(x)cat(2,obj.layerInfo(x).From,obj.layerInfo(x).To);
            
            iv = cellfun(@(str)getIv(str2double(rule.(cat(2,str,'_layer')))),fields,'UniformOutput',false);
            f = cellfun(@(str)str2double(rule.(cat(2,str,'_fraction'))),fields,'UniformOutput',false);
            interval = cellfun(fractionLookup,iv,f);
            %l = cat(1,str2double(rule.y_min_layer), str2double(rule.y_max_layer));
            %f = cat(1,str2double(rule.y_min_fraction), str2double(rule.y_max_fraction));
            %interval = cat(2,fractionLookup(getIv(l(1)),f(1)),fractionLookup(getIv(l(2)),f(2)));
        end                      
        
        function [] = addRulesFromXml(obj,xml)
            ifElseExpansion = @(x,ie)ie{double(x)+1};
            %This relies on lazy evaluation of the if/else condition. If
            %this ever fails just use string returning functions instead of
            %directly returning the string.
            nameValueLookup = @(x,str)ifElseExpansion(any(cellfun(@(s)strcmp(s,str),{x.Name})),{'',x(cellfun(@(s)strcmp(s,str),{x.Name})).Value});
            
            for i = 1:length(xml)
                if(strcmp(xml(i).Name,'global_rule_set'))
                    currMType = 'global';
                else
                    currMType = nameValueLookup(xml(i).Attributes,'mtype');
                end
                obj.ruleSets.(currMType).mtype = currMType;
                %If we ever have other types of rules add that case here.
                rules = xml(i).Children;
                rules = rules(cellfun(@(x)x(1)~='#',{rules.Name}));
                for j = 1:length(rules)
                    id = nameValueLookup(rules(j).Attributes,'id');
                    if(isempty(id))
                        error('XMLPlacementHints:Rules:EmptyIdentifier','This rule has no field "id" specified!');
                    end
                    attr = setdiff({rules(j).Attributes.Name},'id');
                    for k=1:length(attr)
                        obj.ruleSets.(currMType).(id).(attr{k}) = nameValueLookup(rules(j).Attributes,attr{k});
                    end
                end
            end
        end
        
        function [] = makeLayerBins(obj)            
            for i = 1:length(obj.layerInfo)
                borders = linspace(obj.layerInfo(i).From,obj.layerInfo(i).To,...
                    ceil((obj.layerInfo(i).To-obj.layerInfo(i).From)/obj.yBinsSize)+1);
                obj.layerBins{i} = (borders(1:end-1) + borders(2:end))./2;
            end
        end
        
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        %      Specific functions for different rule types       %
        %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
        function scores = checkRegionTarget(obj,instance,rule,bins)            
            minMaxFcn = @(x,y)cat(2,max(x(1),y(1)),min(x(2),y(2)));
            intervalAbs = obj.getLayerInterval(rule,{'y_min','y_max'}); 
            intervalRel = [str2double(instance.y_min) str2double(instance.y_max)];
            scores = cellfun(@(x)diff(minMaxFcn(intervalAbs,intervalRel+x)),num2cell(bins))./min(diff(intervalAbs),diff(intervalRel));
            scores(scores<0)=0;
            scores = scores.^2;
        end
        function scores = checkYBelow(obj,instance,rule,bins)            
            limitAbs = obj.getLayerInterval(rule,{'y'});
            limitRel = str2double(instance.y_max);
            scores = 2.*(limitRel+bins<=limitAbs)-1;            
        end
        
    end
    
    
    methods(Static=true)
        %Implement transfer functions here
        function dat = upper_hard_limit(dat)
            dat(find(dat(2:end)<dat(1:end-1))+1)=0;
        end        
    end
end

